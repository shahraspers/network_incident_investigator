"""
Pluggable data source system for Network Incident Investigator.
Supports: CSV, REST API, Streaming, Database, Cloud Storage, etc.
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class IDataSource(ABC):
    """
    Abstract interface for all data sources.
    Implement this interface to add new data source types.
    """
    
    @abstractmethod
    def load(self, **kwargs) -> pd.DataFrame:
        """
        Load data from source.
        
        Returns:
            DataFrame with columns: timestamp, site_id, metric columns
        """
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate data source is accessible"""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict:
        """Get schema of available data"""
        pass


# ============================================================================
# BUILT-IN DATA SOURCES
# ============================================================================

class CSVDataSource(IDataSource):
    """CSV file data source"""
    
    def __init__(self, filepath: str):
        """
        Initialize CSV data source.
        
        Args:
            filepath: Path to CSV file
        """
        self.filepath = filepath
    
    def load(self, **kwargs) -> pd.DataFrame:
        """Load CSV file"""
        df = pd.read_csv(self.filepath)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    
    def validate(self) -> bool:
        """Check if file exists"""
        import os
        return os.path.exists(self.filepath)
    
    def get_schema(self) -> Dict:
        """Get CSV schema"""
        df = self.load()
        return {
            "columns": df.columns.tolist(),
            "rows": len(df),
            "dtypes": df.dtypes.astype(str).to_dict()
        }


class RestAPIDataSource(IDataSource):
    """REST API data source (e.g., TELUS backend)"""
    
    def __init__(self, endpoint: str, headers: Optional[Dict] = None, params: Optional[Dict] = None):
        """
        Initialize REST API data source.
        
        Args:
            endpoint: API endpoint URL
            headers: HTTP headers (e.g., authorization)
            params: Query parameters (e.g., start_time, end_time)
        """
        self.endpoint = endpoint
        self.headers = headers or {}
        self.params = params or {}
    
    def load(self, **kwargs) -> pd.DataFrame:
        """Load data from REST API"""
        import requests
        
        # Merge kwargs with configured params
        params = {**self.params, **kwargs}
        
        response = requests.get(
            self.endpoint,
            headers=self.headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        
        # Parse response
        data = response.json()
        if isinstance(data, dict) and "data" in data:
            data = data["data"]
        
        df = pd.DataFrame(data)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        return df
    
    def validate(self) -> bool:
        """Check if API is accessible"""
        import requests
        
        try:
            response = requests.head(self.endpoint, timeout=5)
            return response.status_code < 500
        except Exception as e:
            logger.warning(f"API health check failed: {e}")
            return False
    
    def get_schema(self) -> Dict:
        """Get API schema"""
        try:
            df = self.load()
            return {
                "columns": df.columns.tolist(),
                "endpoint": self.endpoint,
                "dtypes": df.dtypes.astype(str).to_dict()
            }
        except Exception as e:
            return {"error": str(e)}


class DatabaseDataSource(IDataSource):
    """SQL Database data source (PostgreSQL, MySQL, etc.)"""
    
    def __init__(self, connection_string: str, query: str):
        """
        Initialize database data source.
        
        Args:
            connection_string: Database connection URL
            query: SQL query to fetch data
        """
        self.connection_string = connection_string
        self.query = query
    
    def load(self, **kwargs) -> pd.DataFrame:
        """Load data from database"""
        import sqlalchemy
        
        engine = sqlalchemy.create_engine(self.connection_string)
        df = pd.read_sql(self.query, engine)
        
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        return df
    
    def validate(self) -> bool:
        """Check database connection"""
        try:
            import sqlalchemy
            engine = sqlalchemy.create_engine(self.connection_string)
            with engine.connect() as conn:
                return True
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
            return False
    
    def get_schema(self) -> Dict:
        """Get database schema"""
        try:
            df = self.load()
            return {
                "columns": df.columns.tolist(),
                "rows": len(df),
                "database": self.connection_string.split("@")[-1].split("/")[0]
            }
        except Exception as e:
            return {"error": str(e)}


class StreamingDataSource(IDataSource):
    """Streaming data source (Kafka, Kinesis, Pub/Sub)"""
    
    def __init__(self, source_type: str, config: Dict):
        """
        Initialize streaming data source.
        
        Args:
            source_type: "kafka", "kinesis", "pubsub"
            config: Source-specific configuration
        """
        self.source_type = source_type
        self.config = config
    
    def load(self, **kwargs) -> pd.DataFrame:
        """Load data from stream"""
        batch_size = kwargs.get("batch_size", 100)
        timeout = kwargs.get("timeout", 30)
        
        if self.source_type == "kafka":
            return self._load_kafka(batch_size, timeout)
        elif self.source_type == "kinesis":
            return self._load_kinesis(batch_size, timeout)
        elif self.source_type == "pubsub":
            return self._load_pubsub(batch_size, timeout)
        else:
            raise ValueError(f"Unknown streaming source: {self.source_type}")
    
    def _load_kafka(self, batch_size: int, timeout: int) -> pd.DataFrame:
        """Load from Kafka"""
        try:
            from kafka import KafkaConsumer
            import json
            
            consumer = KafkaConsumer(
                self.config.get("topic", "network_kpi"),
                bootstrap_servers=self.config.get("bootstrap_servers", "localhost:9092"),
                consumer_timeout_ms=timeout * 1000,
                value_deserializer=lambda m: json.loads(m.decode('utf-8'))
            )
            
            messages = []
            for _, msg in zip(range(batch_size), consumer):
                messages.append(msg.value)
            
            df = pd.DataFrame(messages)
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
        
        except ImportError:
            logger.error("kafka-python not installed. Install with: pip install kafka-python")
            raise
    
    def _load_kinesis(self, batch_size: int, timeout: int) -> pd.DataFrame:
        """Load from AWS Kinesis"""
        try:
            import boto3
            import json
            
            client = boto3.client("kinesis", region_name=self.config.get("region", "us-east-1"))
            
            response = client.describe_stream(StreamName=self.config.get("stream_name", "network-kpi"))
            shard_id = response["StreamDescription"]["Shards"][0]["ShardId"]
            
            shard_iterator = client.get_shard_iterator(
                StreamName=self.config.get("stream_name"),
                ShardId=shard_id,
                ShardIteratorType="LATEST"
            )["ShardIterator"]
            
            messages = []
            for _ in range(batch_size):
                response = client.get_records(ShardIterator=shard_iterator)
                for record in response["Records"]:
                    messages.append(json.loads(record["Data"].decode()))
                shard_iterator = response["NextShardIterator"]
            
            df = pd.DataFrame(messages)
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
        
        except ImportError:
            logger.error("boto3 not installed. Install with: pip install boto3")
            raise
    
    def _load_pubsub(self, batch_size: int, timeout: int) -> pd.DataFrame:
        """Load from Google Pub/Sub"""
        try:
            from google.cloud import pubsub_v1
            import json
            
            subscriber = pubsub_v1.SubscriberClient()
            subscription_path = subscriber.subscription_path(
                self.config.get("project_id"),
                self.config.get("subscription_id", "network-kpi-sub")
            )
            
            messages = []
            
            def callback(message):
                messages.append(json.loads(message.data.decode()))
                message.ack()
            
            streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
            
            # Listen for specified timeout
            import time
            time.sleep(timeout)
            streaming_pull_future.cancel()
            
            df = pd.DataFrame(messages[:batch_size])
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
        
        except ImportError:
            logger.error("google-cloud-pubsub not installed. Install with: pip install google-cloud-pubsub")
            raise
    
    def validate(self) -> bool:
        """Check if stream is accessible"""
        try:
            # Try to load small batch
            self.load(batch_size=1, timeout=5)
            return True
        except Exception as e:
            logger.warning(f"Stream connection failed: {e}")
            return False
    
    def get_schema(self) -> Dict:
        """Get stream schema"""
        try:
            df = self.load(batch_size=10)
            return {
                "columns": df.columns.tolist(),
                "source_type": self.source_type,
                "dtypes": df.dtypes.astype(str).to_dict()
            }
        except Exception as e:
            return {"error": str(e)}


class CloudStorageDataSource(IDataSource):
    """Cloud storage data source (S3, GCS, Azure Blob)"""
    
    def __init__(self, storage_type: str, config: Dict):
        """
        Initialize cloud storage data source.
        
        Args:
            storage_type: "s3", "gcs", "azure"
            config: Storage-specific configuration (bucket, key, etc.)
        """
        self.storage_type = storage_type
        self.config = config
    
    def load(self, **kwargs) -> pd.DataFrame:
        """Load data from cloud storage"""
        if self.storage_type == "s3":
            return self._load_s3()
        elif self.storage_type == "gcs":
            return self._load_gcs()
        elif self.storage_type == "azure":
            return self._load_azure()
        else:
            raise ValueError(f"Unknown storage type: {self.storage_type}")
    
    def _load_s3(self) -> pd.DataFrame:
        """Load from AWS S3"""
        try:
            import boto3
            
            s3 = boto3.client("s3")
            obj = s3.get_object(
                Bucket=self.config.get("bucket"),
                Key=self.config.get("key")
            )
            
            df = pd.read_csv(obj["Body"])
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
        except ImportError:
            logger.error("boto3 not installed")
            raise
    
    def _load_gcs(self) -> pd.DataFrame:
        """Load from Google Cloud Storage"""
        try:
            from google.cloud import storage
            
            client = storage.Client(project=self.config.get("project_id"))
            bucket = client.bucket(self.config.get("bucket"))
            blob = bucket.blob(self.config.get("key"))
            
            csv_content = blob.download_as_string()
            df = pd.read_csv(StringIO(csv_content.decode()))
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
        except ImportError:
            logger.error("google-cloud-storage not installed")
            raise
    
    def _load_azure(self) -> pd.DataFrame:
        """Load from Azure Blob Storage"""
        try:
            from azure.storage.blob import BlobClient
            
            blob = BlobClient.from_connection_string(
                self.config.get("connection_string"),
                container_name=self.config.get("container"),
                blob_name=self.config.get("blob")
            )
            
            csv_content = blob.download_blob().readall()
            df = pd.read_csv(StringIO(csv_content.decode()))
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
            return df
        except ImportError:
            logger.error("azure-storage-blob not installed")
            raise
    
    def validate(self) -> bool:
        """Check if storage is accessible"""
        try:
            self.load()
            return True
        except Exception as e:
            logger.warning(f"Storage connection failed: {e}")
            return False
    
    def get_schema(self) -> Dict:
        """Get storage schema"""
        try:
            df = self.load()
            return {
                "columns": df.columns.tolist(),
                "rows": len(df),
                "storage_type": self.storage_type
            }
        except Exception as e:
            return {"error": str(e)}


# ============================================================================
# DATA SOURCE REGISTRY & FACTORY
# ============================================================================

class DataSourceRegistry:
    """Registry and factory for data sources"""
    
    _sources: Dict[str, type] = {
        "csv": CSVDataSource,
        "rest_api": RestAPIDataSource,
        "database": DatabaseDataSource,
        "streaming": StreamingDataSource,
        "cloud_storage": CloudStorageDataSource,
    }
    
    @classmethod
    def register(cls, name: str, source_class: type) -> None:
        """
        Register a custom data source.
        
        Args:
            name: Source type name
            source_class: Class implementing IDataSource
        """
        if not issubclass(source_class, IDataSource):
            raise TypeError(f"{source_class} must implement IDataSource")
        cls._sources[name] = source_class
        logger.info(f"Registered data source: {name}")
    
    @classmethod
    def create(cls, source_type: str, **kwargs) -> IDataSource:
        """
        Create a data source instance.
        
        Args:
            source_type: Type of data source (csv, rest_api, database, streaming, etc.)
            **kwargs: Source-specific arguments
        
        Returns:
            IDataSource implementation
        
        Raises:
            ValueError: If source_type not found
        """
        if source_type not in cls._sources:
            raise ValueError(f"Unknown data source: {source_type}. Available: {list(cls._sources.keys())}")
        
        source_class = cls._sources[source_type]
        return source_class(**kwargs)
    
    @classmethod
    def list_sources(cls) -> List[str]:
        """List available data sources"""
        return list(cls._sources.keys())
    
    @classmethod
    def get_source_config(cls, source_type: str) -> Dict:
        """Get configuration template for source type"""
        configs = {
            "csv": {"filepath": "path/to/data.csv"},
            "rest_api": {
                "endpoint": "http://api.example.com/data",
                "headers": {"Authorization": "Bearer token"},
                "params": {"start_time": "2026-01-01"}
            },
            "database": {
                "connection_string": "postgresql://user:pass@localhost/db",
                "query": "SELECT * FROM network_kpi"
            },
            "streaming": {
                "source_type": "kafka",  # or "kinesis", "pubsub"
                "config": {
                    "bootstrap_servers": "localhost:9092",
                    "topic": "network_kpi"
                }
            },
            "cloud_storage": {
                "storage_type": "s3",  # or "gcs", "azure"
                "config": {
                    "bucket": "my-bucket",
                    "key": "data/kpi.csv"
                }
            }
        }
        return configs.get(source_type, {})
