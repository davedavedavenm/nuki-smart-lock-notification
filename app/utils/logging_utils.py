"""
Common logging utilities for Nuki Smart Lock Notification System.
Provides standardized logging configuration across all components.
"""
import os
import sys
import logging
import logging.handlers
from pathlib import Path
import json
from datetime import datetime

class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    Formats log records as JSON objects for easier parsing and analysis.
    """
    
    def format(self, record):
        """Format the log record as a JSON object."""
        log_record = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if available
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add custom fields if available
        if hasattr(record, 'data') and record.data:
            log_record['data'] = record.data
            
        return json.dumps(log_record)

class LoggerConfigurator:
    """
    Configures the logging system for the Nuki Smart Lock Notification System.
    Provides methods to set up logging for different components.
    """
    
    def __init__(self, logs_dir=None, app_name='nuki_monitor'):
        """
        Initialize the logger configurator.
        
        Args:
            logs_dir: Directory for log files. If None, will use environment variable or default.
            app_name: Application name used for the logger.
        """
        self.app_name = app_name
        
        # Determine log directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.logs_dir = logs_dir or os.environ.get('LOGS_DIR') or os.path.join(base_dir, 'logs')
        
        # Create logs directory if it doesn't exist
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Default log levels
        self.levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
    
    def configure_logger(self, logger_name=None, log_level='INFO', 
                        console=True, log_file=None, json_format=False, 
                        max_bytes=10485760, backup_count=5):
        """
        Configure a logger with the specified parameters.
        
        Args:
            logger_name: Name of the logger to configure. If None, uses app_name.
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            console: Whether to log to console.
            log_file: Log file name. If None, uses '{app_name}.log'.
            json_format: Whether to use JSON format for logs.
            max_bytes: Maximum log file size before rotation.
            backup_count: Number of backup log files to keep.
            
        Returns:
            logging.Logger: Configured logger instance.
        """
        # Get logger
        logger_name = logger_name or self.app_name
        logger = logging.getLogger(logger_name)
        
        # Set log level
        level = self.levels.get(log_level.upper(), logging.INFO)
        logger.setLevel(level)
        
        # Remove existing handlers to prevent duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Determine formatters
        if json_format:
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        # Add console handler if requested
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # Add file handler if log file is specified or use default
        if log_file is not True and log_file is not False:
            if log_file is None:
                log_file = f"{self.app_name}.log"
            
            # Convert to absolute path if not already
            if not os.path.isabs(log_file):
                log_file = os.path.join(self.logs_dir, log_file)
            
            # Create rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # Don't propagate to root logger
        logger.propagate = False
        
        return logger
    
    def configure_werkzeug_logger(self, log_level='INFO', log_file='web_access.log'):
        """
        Configure the Werkzeug logger used by Flask for access logs.
        
        Args:
            log_level: Logging level for Werkzeug logger.
            log_file: Log file for Werkzeug access logs.
            
        Returns:
            logging.Logger: Configured Werkzeug logger.
        """
        werkzeug_logger = logging.getLogger('werkzeug')
        
        # Set log level
        level = self.levels.get(log_level.upper(), logging.INFO)
        werkzeug_logger.setLevel(level)
        
        # Remove existing handlers to prevent duplicates
        for handler in werkzeug_logger.handlers[:]:
            werkzeug_logger.removeHandler(handler)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add file handler
        log_file_path = os.path.join(self.logs_dir, log_file)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file_path,
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        werkzeug_logger.addHandler(file_handler)
        
        # Don't propagate to root logger
        werkzeug_logger.propagate = False
        
        return werkzeug_logger
    
    def get_logger(self, name=None):
        """
        Get a logger by name. If it doesn't exist, creates a default one.
        
        Args:
            name: Name of the logger to get. If None, uses app_name.
            
        Returns:
            logging.Logger: Logger instance.
        """
        name = name or self.app_name
        logger = logging.getLogger(name)
        
        # If logger doesn't have handlers, configure it with defaults
        if not logger.handlers:
            return self.configure_logger(logger_name=name)
        
        return logger

def get_logger(name=None, logs_dir=None, log_level='INFO'):
    """
    Convenience function to get a logger with standard configuration.
    
    Args:
        name: Logger name. If None, uses 'nuki_monitor'.
        logs_dir: Directory for log files. If None, uses environment variable or default.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        
    Returns:
        logging.Logger: Configured logger instance.
    """
    configurator = LoggerConfigurator(logs_dir=logs_dir)
    return configurator.configure_logger(logger_name=name, log_level=log_level)

class LoggingContext:
    """
    Context manager for adding contextual information to log records.
    Allows adding temporary fields to log records within a context.
    """
    
    def __init__(self, logger, **kwargs):
        """
        Initialize the logging context.
        
        Args:
            logger: Logger instance to enhance.
            **kwargs: Context data to add to log records.
        """
        self.logger = logger
        self.context = kwargs
        self.old_factory = logging.getLogRecordFactory()
    
    def __enter__(self):
        """Enter the context and set up the record factory."""
        logging.setLogRecordFactory(self._record_factory)
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and restore the original record factory."""
        logging.setLogRecordFactory(self.old_factory)
    
    def _record_factory(self, *args, **kwargs):
        """Create a log record with additional context data."""
        record = self.old_factory(*args, **kwargs)
        record.data = getattr(record, 'data', {})
        record.data.update(self.context)
        return record

def log_with_context(logger, level, message, **kwargs):
    """
    Log a message with additional context data.
    
    Args:
        logger: Logger instance to use.
        level: Logging level (e.g., 'INFO', 'ERROR').
        message: Log message.
        **kwargs: Context data to add to the log record.
    """
    with LoggingContext(logger, **kwargs):
        logger_method = getattr(logger, level.lower())
        logger_method(message)
