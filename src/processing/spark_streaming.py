#!/usr/bin/env python3
"""
SensorFlow - Spark Streaming Processor
"""
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.clustering import KMeans
from pyspark.sql.window import Window
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SensorStreamProcessor:
    def __init__(self, kafka_bootstrap_servers="localhost:9092", influxdb_url="http://localhost:8086"):
        self.kafka_servers = kafka_bootstrap_servers
        self.influxdb_url = influxdb_url
        self.spark = SparkSession.builder \
            .appName("SensorFlow-StreamProcessor") \
            .config("spark.sql.adaptive.enabled", "true") \
            .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
            .config("spark.sql.streaming.metricsEnabled", "true") \
            .getOrCreate()
        self.spark.sparkContext.setLogLevel("WARN")
        self.sensor_schema = StructType([
            StructField("sensor_id", StringType(), True),
            StructField("sensor_type", StringType(), True),
            StructField("location", StringType(), True),
            StructField("timestamp", StringType(), True),
            StructField("value", DoubleType(), True),
            StructField("unit", StringType(), True),
            StructField("status", StringType(), True),
            StructField("metadata", MapType(StringType(), StringType()), True)
        ])
    def create_kafka_stream(self, topics=["sensors.temperature", "sensors.vibration", "sensors.pressure", "sensors.humidity"]):
        kafka_df = self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", self.kafka_servers) \
            .option("subscribe", ",".join(topics)) \
            .option("startingOffsets", "latest") \
            .option("failOnDataLoss", "false") \
            .load()
        parsed_df = kafka_df.select(
            col("topic"),
            col("partition"),
            col("offset"),
            col("timestamp").alias("kafka_timestamp"),
            from_json(col("value").cast("string"), self.sensor_schema).alias("data")
        ).select(
            col("topic"),
            col("kafka_timestamp"),
            col("data.*")
        )
        processed_df = parsed_df \
            .withColumn("processing_time", current_timestamp()) \
            .withColumn("sensor_timestamp", to_timestamp(col("timestamp"))) \
            .withColumn("hour", hour(col("sensor_timestamp"))) \
            .withColumn("day", dayofyear(col("sensor_timestamp")))
        return processed_df
    def detect_anomalies(self, df):
        window_spec = Window.partitionBy("sensor_type", "location") \
                           .orderBy("sensor_timestamp") \
                           .rowsBetween(-100, 0)
        anomaly_df = df.withColumn(
            "rolling_mean", avg("value").over(window_spec)
        ).withColumn(
            "rolling_std", expr("sqrt(avg(pow(value - rolling_mean, 2)))").over(window_spec)
        ).withColumn(
            "z_score", when(col("rolling_std") > 0, abs(col("value") - col("rolling_mean")) / col("rolling_std")).otherwise(0)
        ).withColumn(
            "is_anomaly_statistical", col("z_score") > 3.0
        ).withColumn(
            "is_anomaly_status", col("status").isin(["HIGH_ALARM", "LOW_ALARM"])
        ).withColumn(
            "is_anomaly", col("is_anomaly_statistical") | col("is_anomaly_status")
        )
        return anomaly_df
    def create_aggregations(self, df):
        minute_agg = df \
            .withWatermark("sensor_timestamp", "2 minutes") \
            .groupBy(
                window(col("sensor_timestamp"), "1 minute"),
                "sensor_type",
                "location"
            ).agg(
                count("*").alias("reading_count"),
                avg("value").alias("avg_value"),
                min("value").alias("min_value"),
                max("value").alias("max_value"),
                stddev("value").alias("stddev_value"),
                sum(when(col("is_anomaly"), 1).otherwise(0)).alias("anomaly_count"),
                collect_list("sensor_id").alias("sensor_ids")
            ).select(
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
                "*"
            ).drop("window")
        hour_agg = df \
            .withWatermark("sensor_timestamp", "1 hour") \
            .groupBy(
                window(col("sensor_timestamp"), "1 hour"),
                "sensor_type",
                "location"
            ).agg(
                count("*").alias("reading_count"),
                avg("value").alias("avg_value"),
                min("value").alias("min_value"),
                max("value").alias("max_value"),
                sum(when(col("is_anomaly"), 1).otherwise(0)).alias("anomaly_count")
            ).select(
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
                "*"
            ).drop("window")
        return minute_agg, hour_agg
    def write_to_console(self, df, query_name, output_mode="append"):
        query = df.writeStream \
            .queryName(query_name) \
            .outputMode(output_mode) \
            .format("console") \
            .option("truncate", "false") \
            .option("numRows", 20) \
            .trigger(processingTime="10 seconds") \
            .start()
        return query
    def write_to_kafka(self, df, output_topic, query_name):
        kafka_output = df.select(
            col("sensor_id").alias("key"),
            to_json(struct([col(c) for c in df.columns])).alias("value")
        )
        query = kafka_output.writeStream \
            .queryName(query_name) \
            .format("kafka") \
            .option("kafka.bootstrap.servers", self.kafka_servers) \
            .option("topic", output_topic) \
            .option("checkpointLocation", f"/tmp/checkpoint/{query_name}") \
            .outputMode("append") \
            .trigger(processingTime="5 seconds") \
            .start()
        return query
    def run_processing_pipeline(self):
        logger.info("Starting SensorFlow Stream Processing Pipeline")
        raw_stream = self.create_kafka_stream()
        anomaly_stream = self.detect_anomalies(raw_stream)
        minute_agg, hour_agg = self.create_aggregations(anomaly_stream)
        raw_query = self.write_to_kafka(anomaly_stream.filter(col("is_anomaly") == True), "alerts.anomalies", "anomaly_alerts")
        minute_query = self.write_to_kafka(minute_agg, "aggregations.minute", "minute_aggregations")
        hour_query = self.write_to_kafka(hour_agg, "aggregations.hour", "hour_aggregations")
        console_query = self.write_to_console(anomaly_stream.filter(col("is_anomaly") == True), "anomaly_console")
        queries = [raw_query, minute_query, hour_query, console_query]
        logger.info("All streaming queries started")
        try:
            for query in queries:
                query.awaitTermination()
        except KeyboardInterrupt:
            logger.info("Stopping streaming queries...")
            for query in queries:
                query.stop()
        finally:
            self.spark.stop()
def main():
    import argparse
    parser = argparse.ArgumentParser(description="SensorFlow Stream Processor")
    parser.add_argument("--kafka-servers", default="localhost:9092", help="Kafka bootstrap servers")
    parser.add_argument("--influxdb-url", default="http://localhost:8086", help="InfluxDB URL")
    args = parser.parse_args()
    processor = SensorStreamProcessor(kafka_bootstrap_servers=args.kafka_servers, influxdb_url=args.influxdb_url)
    processor.run_processing_pipeline()
if __name__ == "__main__":
    main()
