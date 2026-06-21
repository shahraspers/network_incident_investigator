"""
Pluggable data source loaders for different input formats.
Supports: CSV files, backend APIs, and streaming sources.
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DataSource(ABC):
    """Abstract base class for data sources"""
    
    @abstractmethod
    def load(self) -> pd.DataFrame:
        """Load data from source"""
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """Validate data source connectivity"""
        pass


class CSVDataSource(DataSource):
    """Load data from CSV files"""
    
    def __init__(
        self,
        filepath: str,
        timestamp_col: str = "timestamp",
        parse_dates: bool = True,
        **kwargs
    ):
        """
        Initialize CSV data source.
        
        Args:
            filepath: Path to CSV file
            timestamp_col: Name of timestamp column
            parse_dates: Whether to parse timestamp column as datetime
            **kwargs: Additional pandas read_csv parameters
        """
        self.filepath = filepath
        self.timestamp_col = timestamp_col
        self.parse_dates = parse_dates
        self.kwargs = kwargs
    
    def validate(self) -> bool:
        """Check if file exists"""
        return Path(self.filepath).exists()
    
    def load(self) -> pd.DataFrame:
        """Load CSV file"""
        try:
            if self.parse_dates:
                df = pd.read_csv(
                    self.filepath,
                    parse_dates=[self.timestamp_col],
                    **self.kwargs
                )
            else:
                df = pd.read_csv(self.filepath, **self.kwargs)
            
            logger.info(f"Loaded {len(df)} rows from {self.filepath}")
            return df
        
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            raise


class BackendAPIDataSource(DataSource):
    """Load data from backend API (placeholder for integration)"""
    
    def __init__(
        self,
        endpoint: str,
        site_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout: int = 30,
        **kwargs
    ):
        """
        Initialize backend API data source.
        
        Args:
            endpoint: API endpoint URL
            site_id: Optional site ID to filter by
            start_time: Optional start time for data range
            end_time: Optional end time for data range
            auth_token: Optional authentication token
            timeout: Request timeout in seconds
            **kwargs: Additional parameters for API call
        """
        self.endpoint = endpoint
        self.site_id = site_id
        self.start_time = start_time
        self.end_time = end_time
        self.auth_token = auth_token
        self.timeout = timeout
        self.kwargs = kwargs
    
    def validate(self) -> bool:
        """Check API connectivity"""
        try:
            import requests
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            response = requests.head(self.endpoint, timeout=5, headers=headers)
            return response.status_code < 400
        except Exception as e:
            logger.warning(f"Backend API validation failed: {e}")
            return False
    
    def load(self) -> pd.DataFrame:
        """
        Load data from backend API.
        
        Note: This is a placeholder. Implement based on actual backend API spec.
        """
        try:
            import requests
            
            params = {
                "site_id": self.site_id,
                "start_time": self.start_time,
                "end_time": self.end_time,
                **self.kwargs
            }
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            response = requests.get(
                self.endpoint,
                params=params,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            # Parse response - adapt based on actual API format
            data = response.json()
            
            # Assume API returns list of records or records key
            records = data.get("records", data) if isinstance(data, dict) else data
            df = pd.DataFrame(records)
            
            logger.info(f"Loaded {len(df)} rows from backend API")
            return df
        
        except Exception as e:
            logger.error(f"Error loading from backend API: {e}")
            raise


class StreamingDataSource(DataSource):
    """Load data from streaming source (placeholder for integration)"""
    
    def __init__(
        self,
        source_config: Dict,
        batch_size: int = 100,
        timeout: int = 30,
        **kwargs
    ):
        """
        Initialize streaming data source.
        
        Args:
            source_config: Configuration for streaming source
                (Kafka, Kinesis, Pub/Sub, etc.)
            batch_size: Number of messages to batch
            timeout: Read timeout in seconds
            **kwargs: Additional streaming parameters
        """
        self.source_config = source_config
        self.batch_size = batch_size
        self.timeout = timeout
        self.kwargs = kwargs
    
    def validate(self) -> bool:
        """Check streaming source connectivity"""
        logger.info("Streaming data source - validation is environment dependent")
        return bool(self.source_config)
    
    def load(self) -> pd.DataFrame:
        """
        Load data from streaming source.
        
        Note: This is a placeholder. Implement based on actual streaming platform.
        """
        source_type = self.source_config.get("type", "kafka")
        
        logger.info(f"Attempting to load from {source_type} streaming source")
        
        # Placeholder implementation
        if source_type == "kafka":
            return self._load_from_kafka()
        elif source_type == "kinesis":
            return self._load_from_kinesis()
        elif source_type == "pubsub":
            return self._load_from_pubsub()
        else:
            raise ValueError(f"Unsupported streaming source: {source_type}")
    
    def _load_from_kafka(self) -> pd.DataFrame:
        """Load from Kafka - placeholder"""
        logger.info("Kafka integration - placeholder")
        # In production: from kafka import KafkaConsumer
        raise NotImplementedError("Kafka integration not yet implemented")
    
    def _load_from_kinesis(self) -> pd.DataFrame:
        """Load from AWS Kinesis - placeholder"""
        logger.info("Kinesis integration - placeholder")
        # In production: import boto3
        raise NotImplementedError("Kinesis integration not yet implemented")
    
    def _load_from_pubsub(self) -> pd.DataFrame:
        """Load from Google Pub/Sub - placeholder"""
        logger.info("Pub/Sub integration - placeholder")
        # In production: from google.cloud import pubsub_v1
        raise NotImplementedError("Pub/Sub integration not yet implemented")


class DataSourceFactory:
    """Factory for creating data sources"""
    
    @staticmethod
    def create(source_type: str, config: Dict) -> DataSource:
        """
        Create a data source.
        
        Args:
            source_type: One of 'csv', 'backend_api', 'streaming'
            config: Source-specific configuration
        
        Returns:
            DataSource instance
        
        Examples:
            CSV:
            >>> factory = DataSourceFactory()
            >>> source = factory.create('csv', {'filepath': 'data.csv'})
            
            Backend API:
            >>> source = factory.create('backend_api', {
            ...     'endpoint': 'https://api.telus.com/metrics',
            ...     'site_id': 'CELL_001'
            ... })
            
            Streaming:
            >>> source = factory.create('streaming', {
            ...     'type': 'kafka',
            ...     'brokers': ['localhost:9092'],
            ...     'topic': 'network_metrics'
            ... })
        """
        if source_type == "csv":
            return CSVDataSource(**config)
        
        elif source_type == "backend_api":
            return BackendAPIDataSource(**config)
        
        elif source_type == "streaming":
            return StreamingDataSource(**config)
        
        else:
            raise ValueError(f"Unknown source type: {source_type}")


# Convenience functions for each loader type

def load_data_from_csv(
    filepath: str,
    timestamp_col: str = "timestamp",
    parse_dates: bool = True,
    **kwargs
) -> pd.DataFrame:
    """
    Load data from CSV file.
    
    Args:
        filepath: Path to CSV file
        timestamp_col: Name of timestamp column
        parse_dates: Whether to parse as datetime
        **kwargs: Additional pandas read_csv parameters
    
    Returns:
        DataFrame with loaded data
    """
    source = CSVDataSource(
        filepath=filepath,
        timestamp_col=timestamp_col,
        parse_dates=parse_dates,
        **kwargs
    )
    return source.load()


def load_data_from_backend(config: Dict) -> pd.DataFrame:
    """
    Load data from backend API.
    
    Args:
        config: Backend API configuration with keys:
            - endpoint (required): API endpoint URL
            - site_id (optional): Site ID to filter
            - start_time (optional): Start time for query
            - end_time (optional): End time for query
            - auth_token (optional): Authentication token
    
    Returns:
        DataFrame with loaded data
    
    Example:
        >>> config = {
        ...     'endpoint': 'https://api.telus.com/metrics',
        ...     'site_id': 'CELL_001',
        ...     'start_time': '2026-06-20T00:00:00Z'
        ... }
        >>> df = load_data_from_backend(config)
    """
    source = BackendAPIDataSource(**config)
    return source.load()


def load_data_from_stream(config: Dict) -> pd.DataFrame:
    """
    Load data from streaming source.
    
    Args:
        config: Streaming source configuration with keys:
            - type (required): 'kafka', 'kinesis', or 'pubsub'
            - source-specific parameters (brokers, topic, etc.)
    
    Returns:
        DataFrame with loaded data
    
    Example:
        >>> config = {
        ...     'type': 'kafka',
        ...     'brokers': ['localhost:9092'],
        ...     'topic': 'network_metrics'
        ... }
        >>> df = load_data_from_stream(config)
    """
    source = StreamingDataSource(source_config=config)
    return source.load()


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Example: Load from CSV
    try:
        df = load_data_from_csv("./data/sample_data_1.csv")
        print(f"Loaded CSV: {len(df)} rows")
    except Exception as e:
        print(f"CSV load error: {e}")
    
    # Example: Backend API (placeholder)
    # backend_config = {
    #     'endpoint': 'https://api.telus.com/metrics',
    #     'site_id': 'CELL_001'
    # }
    # df = load_data_from_backend(backend_config)
    
    # Example: Streaming (placeholder)
    # stream_config = {
    #     'type': 'kafka',
    #     'brokers': ['localhost:9092'],
    #     'topic': 'network_metrics'
    # }
    # df = load_data_from_stream(stream_config)
