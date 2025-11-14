"""
db.py - Database handler for storing and retrieving metadata
Description: This module provides functionality to interact with a SQLite database for storing and retrieving metadata.
Author: Eric Hiss (GitHub: EricRollei)
Contact: [eric@historic.camera, eric@rollei.us]
Version: 1.0.0
Date: [March 2025]
License: Dual License (Non-Commercial and Commercial Use)
Copyright (c) 2025 Eric Hiss. All rights reserved.

Dual License:
1. Non-Commercial Use: This software is licensed under the terms of the
   Creative Commons Attribution-NonCommercial 4.0 International License.
   To view a copy of this license, visit http://creativecommons.org/licenses/by-nc/4.0/
   
2. Commercial Use: For commercial use, a separate license is required.
   Please contact Eric Hiss at [eric@historic.camera, eric@rollei.us] for licensing options.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
PARTICULAR PURPOSE AND NONINFRINGEMENT.

Dependencies:
This code depends on several third-party libraries, each with its own license:

"""
# Metadata_system/src/eric_metadata/handlers/db.py
import os
import sqlite3
import json
from typing import Dict, Any, List, Optional, Tuple, Union
import datetime
import re

from ..handlers.base import BaseHandler
from ..utils.error_handling import ErrorRecovery

class DatabaseHandler(BaseHandler):
    """Handler for database storage of metadata"""
    
    def __init__(self, debug: bool = False, db_path: Optional[str] = None):
        """
        Initialize the database handler
        
        Args:
            debug: Whether to enable debug logging
            db_path: Path to the database file (default: 'metadata.db' in current directory)
        """
        super().__init__(debug)
        
        # Set database path
        self.db_path = db_path or os.path.join(os.getcwd(), 'metadata.db')
        self.conn = None
        self.cursor = None
        
        # Initialize database
        self._initialize_db()
    
    def _initialize_db(self) -> bool:
        """Initialize database and create tables if they don't exist"""
        try:
            # Connect to database
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            self.cursor = self.conn.cursor()
            
            # Create tables if they don't exist
            self._create_tables()
            
            # Run schema migrations
            self._migrate_schema()
            
            self.log(f"Database initialized at {self.db_path}", level="INFO")
            return True
        except Exception as e:
            self.log(f"Database initialization failed: {str(e)}", level="ERROR", error=e)
            self.conn = None
            self.cursor = None
            return False
            
    def _create_tables(self) -> None:
        """Create database tables for metadata storage"""
        try:
            # Create images table (basic info)
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY,
                filepath TEXT UNIQUE,
                filename TEXT,
                format TEXT,
                width INTEGER,
                height INTEGER,
                orientation TEXT,
                has_text BOOLEAN,
                title TEXT,
                description TEXT,
                rating INTEGER,
                created_date TEXT,
                updated_date TEXT
            )
            ''')
            
            # Create scores table (for all numeric measurements)
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS scores (
                image_id INTEGER,
                category TEXT,
                metric TEXT,
                value REAL,
                higher_better BOOLEAN,
                timestamp TEXT,
                FOREIGN KEY (image_id) REFERENCES images(id),
                UNIQUE(image_id, category, metric)
            )
            ''')
            
            # Create keywords table
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                image_id INTEGER,
                keyword TEXT,
                FOREIGN KEY (image_id) REFERENCES images(id),
                UNIQUE(image_id, keyword)
            )
            ''')
            
            # Create classifications table (for style, color mode, etc.)
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS classifications (
                image_id INTEGER,
                category TEXT,
                value TEXT,
                confidence REAL,
                timestamp TEXT,
                FOREIGN KEY (image_id) REFERENCES images(id),
                UNIQUE(image_id, category)
            )
            ''')
            
            # Create ai_info table (for generation parameters)
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_info (
                image_id INTEGER,
                model TEXT,
                positive_prompt TEXT,
                negative_prompt TEXT,
                sampler TEXT,
                seed INTEGER,
                steps INTEGER,
                cfg_scale REAL,
                timestamp TEXT,
                FOREIGN KEY (image_id) REFERENCES images(id)
            )
            ''')
            
            # Create regions table (for faces, areas)
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS regions (
                id INTEGER PRIMARY KEY,
                image_id INTEGER,
                type TEXT,
                name TEXT,
                x REAL,
                y REAL,
                w REAL,
                h REAL,
                data TEXT,  -- JSON for additional attributes
                FOREIGN KEY (image_id) REFERENCES images(id)
            )
            ''')
            
            # Create metadata_json table (for additional metadata storage)
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata_json (
                image_id INTEGER,
                section TEXT,
                data TEXT,  -- JSON data
                FOREIGN KEY (image_id) REFERENCES images(id),
                UNIQUE(image_id, section)
            )
            ''')
            
            # Create indexes for better performance
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_filepath ON images(filepath)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_scores ON scores(category, metric)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_keywords ON keywords(keyword)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_classifications ON classifications(category, value)')
            self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_model ON ai_info(model)')
            
            # Commit changes
            self.conn.commit()
            
        except Exception as e:
            self.log(f"Table creation failed: {str(e)}", level="ERROR", error=e)
            raise
    
    def _migrate_schema(self) -> None:
        """Migrate database schema to latest version"""
        try:
            # Check current schema version by examining table structure
            self.cursor.execute("PRAGMA table_info(images)")
            columns = {row[1]: row[2] for row in self.cursor.fetchall()}
            
            migrations_applied = []
            
            # Migration 1: Add missing columns to images table
            missing_columns = {
                'title': 'TEXT',
                'description': 'TEXT', 
                'rating': 'INTEGER'
            }
            
            for column, column_type in missing_columns.items():
                if column not in columns:
                    self.cursor.execute(f"ALTER TABLE images ADD COLUMN {column} {column_type}")
                    migrations_applied.append(f"Added {column} column")
                    
            if migrations_applied:
                self.conn.commit()
                self.log(f"Applied database migrations: {', '.join(migrations_applied)}", level="INFO")
            else:
                self.log("Database schema is up to date", level="DEBUG")
                
        except Exception as e:
            self.log(f"Schema migration failed: {str(e)}", level="ERROR", error=e)
            # Don't raise here - let the database continue to work with existing schema
    
    def write_metadata(self, filepath: str, metadata: Dict[str, Any]) -> bool:
        """
        Write metadata to database
        
        Args:
            filepath: Path to the file
            metadata: Metadata to write
            
        Returns:
            bool: True if successful
        """
        try:
            # Validate connection first
            if self.conn is None:
                self.log("Database connection not available", level="ERROR")
                return False

            # Get file information
            filename = os.path.basename(filepath)
            file_format = os.path.splitext(filename)[1].lower()
            
            # Begin transaction
            self.cursor.execute("BEGIN TRANSACTION")
            
            # Insert or update image record
            self._insert_or_update_image(filepath, filename, file_format, metadata)
            
            # Get image ID
            self.cursor.execute("SELECT id FROM images WHERE filepath = ?", (filepath,))
            row = self.cursor.fetchone()
            if not row:
                raise ValueError(f"Failed to get image ID for {filepath}")
                
            image_id = row['id']
            
            # Process different metadata sections
            if 'basic' in metadata:
                self._handle_basic_metadata(image_id, metadata['basic'])
                
            if 'analysis' in metadata:
                self._handle_analysis_metadata(image_id, metadata['analysis'])
                
            if 'ai_info' in metadata:
                self._handle_ai_metadata(image_id, metadata['ai_info'])
                
            if 'regions' in metadata:
                self._handle_region_metadata(image_id, metadata['regions'])
                
            # Update image updated_date
            self.cursor.execute(
                "UPDATE images SET updated_date = ? WHERE id = ?",
                (self.get_timestamp(), image_id)
            )
            
            # Commit transaction
            self.conn.commit()
            
            return True
            
        except Exception as e:
            # Rollback transaction if connection exists
            if self.conn is not None:
                try:
                    self.conn.rollback()
                except Exception as rollback_error:
                    self.log(f"Rollback failed: {str(rollback_error)}", level="ERROR")
                    
            self.log(f"Database write failed: {str(e)}", level="ERROR", error=e)
            
            # Attempt recovery
            context = {
                'filepath': filepath,
                'metadata': metadata,
                'error_type': type(e).__name__,
                'error': str(e)
            }
            
            return ErrorRecovery.recover_write_error(self, context)
    
    def read_metadata(self, filepath: str) -> Dict[str, Any]:
        """
        Read metadata from database
        
        Args:
            filepath: Path to the file
            
        Returns:
            dict: Metadata from database
        """
        try:
            # Get image ID
            self.cursor.execute("SELECT id FROM images WHERE filepath = ?", (filepath,))
            row = self.cursor.fetchone()
            if not row:
                return {}
                
            image_id = row['id']
            
            # Create result structure
            result = {
                'basic': {},
                'analysis': {},
                'ai_info': {}
            }
            
            # Read basic metadata
            self._read_basic_metadata(image_id, result)
            
            # Read analysis metadata
            self._read_analysis_metadata(image_id, result)
            
            # Read AI info
            self._read_ai_metadata(image_id, result)
            
            # Read regions
            self._read_region_metadata(image_id, result)
            
            return result
            
        except Exception as e:
            self.log(f"Database read failed: {str(e)}", level="ERROR", error=e)
            
            # Attempt recovery
            context = {
                'filepath': filepath,
                'error_type': type(e).__name__,
                'error': str(e)
            }
            
            return ErrorRecovery.recover_read_error(self, context)
    
    def _insert_or_update_image(self, filepath: str, filename: str, file_format: str, 
                              metadata: Dict[str, Any]) -> None:
        """
        Insert or update image record
        
        Args:
            filepath: Path to the file
            filename: File name
            file_format: File format
            metadata: Metadata containing dimension info
        """
        # Get dimensions if available
        width = None
        height = None
        orientation = None
        has_text = None
        
        # Extract dimensions from metadata if available
        if 'analysis' in metadata:
            analysis = metadata['analysis']
            
            # Check for dimensions
            if 'dimensions' in analysis:
                dims = analysis['dimensions']
                width = dims.get('width')
                height = dims.get('height')
                if width and height:
                    orientation = 'landscape' if width > height else 'portrait' if height > width else 'square'
            
            # Check for classification data
            if 'classification' in analysis:
                has_text = 'text_detected' in str(analysis['classification'])
        
        # Insert or update image record
        self.cursor.execute("""
        INSERT INTO images (
            filepath, filename, format, width, height, orientation, has_text, 
            created_date, updated_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(filepath) DO UPDATE SET
            width = COALESCE(excluded.width, width),
            height = COALESCE(excluded.height, height),
            orientation = COALESCE(excluded.orientation, orientation),
            has_text = COALESCE(excluded.has_text, has_text),
            updated_date = excluded.updated_date
        """, (
            filepath, filename, file_format, width, height, orientation, has_text,
            self.get_timestamp(), self.get_timestamp()
        ))
    
    def _handle_basic_metadata(self, image_id: int, basic_data: Dict[str, Any]) -> None:
        """
        Handle basic metadata section
        
        Args:
            image_id: Image ID
            basic_data: Basic metadata
        """
        # Update basic fields in images table
        if 'title' in basic_data:
            self.cursor.execute(
                "UPDATE images SET title = ? WHERE id = ?",
                (basic_data['title'], image_id)
            )
            
        if 'description' in basic_data:
            self.cursor.execute(
                "UPDATE images SET description = ? WHERE id = ?",
                (basic_data['description'], image_id)
            )
            
        if 'rating' in basic_data:
            self.cursor.execute(
                "UPDATE images SET rating = ? WHERE id = ?",
                (basic_data['rating'], image_id)
            )
            
        # Handle keywords
        if 'keywords' in basic_data and basic_data['keywords']:
            keywords = basic_data['keywords']
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(',')]
            elif not isinstance(keywords, (list, tuple, set)):
                keywords = [str(keywords)]
                
            # Insert keywords
            for keyword in keywords:
                self.cursor.execute("""
                INSERT OR IGNORE INTO keywords (image_id, keyword)
                VALUES (?, ?)
                """, (image_id, keyword))
    
    def _handle_analysis_metadata(self, image_id: int, analysis_data: Dict[str, Any]) -> None:
        """
        Handle analysis metadata section
        
        Args:
            image_id: Image ID
            analysis_data: Analysis metadata
        """
        for analysis_type, data in analysis_data.items():
            if isinstance(data, dict):
                self._process_analysis_section(image_id, analysis_type, data)
    
    def _process_analysis_section(self, image_id: int, section: str, data: Dict[str, Any], 
                                 prefix: str = "") -> None:
        """
        Process analysis section recursively
        
        Args:
            image_id: Image ID
            section: Section name
            data: Section data
            prefix: Key prefix for nested data
        """
        for key, value in data.items():
            if isinstance(value, dict):
                # Check if this is a measurement with score/confidence
                if 'score' in value:
                    metric = f"{prefix}{key}" if prefix else key
                    self._store_score(
                        image_id, 
                        section, 
                        metric, 
                        value['score'], 
                        value.get('higher_better', True),
                        value.get('timestamp')
                    )
                else:
                    # Recursive handling of nested structure
                    nested_prefix = f"{prefix}{key}." if prefix else f"{key}."
                    self._process_analysis_section(image_id, section, value, nested_prefix)
            elif isinstance(value, (int, float)) and not key.startswith('_'):
                # Direct numeric value (assumed to be a score/measurement)
                metric = f"{prefix}{key}" if prefix else key
                self._store_score(image_id, section, metric, value, True)
            elif key.lower() in ('type', 'mode', 'style', 'category') and isinstance(value, str):
                # Handle classifications
                self.cursor.execute("""
                INSERT OR REPLACE INTO classifications 
                (image_id, category, value, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """, (image_id, key, value, 1.0, self.get_timestamp()))
    
    def _store_score(self, image_id: int, category: str, metric: str, value: float,
                   higher_better: bool, timestamp: Optional[str] = None) -> None:
        """
        Store score in database
        
        Args:
            image_id: Image ID
            category: Score category
            metric: Metric name
            value: Score value
            higher_better: Whether higher value is better
            timestamp: Optional timestamp
        """
        self.cursor.execute("""
        INSERT OR REPLACE INTO scores 
        (image_id, category, metric, value, higher_better, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            image_id, 
            category, 
            metric, 
            float(value), 
            higher_better, 
            timestamp or self.get_timestamp()
        ))
    
    def _handle_ai_metadata(self, image_id: int, ai_data: Dict[str, Any]) -> None:
        """
        Handle AI metadata section
        
        Args:
            image_id: Image ID
            ai_data: AI metadata
        """
        # Process generation data
        if 'generation' in ai_data:
            gen_data = ai_data['generation']
            
            self.cursor.execute("""
            INSERT OR REPLACE INTO ai_info 
            (image_id, model, positive_prompt, negative_prompt, sampler, seed, 
             steps, cfg_scale, timestamp) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                image_id,
                gen_data.get('model'),
                gen_data.get('prompt'),
                gen_data.get('negative_prompt'),
                gen_data.get('sampler'),
                gen_data.get('seed'),
                gen_data.get('steps'),
                gen_data.get('cfg_scale'),
                gen_data.get('timestamp') or self.get_timestamp()
            ))
            
            # Process LoRAs if present
            if 'loras' in gen_data and isinstance(gen_data['loras'], list):
                for lora in gen_data['loras']:
                    # Store LoRAs in a separate table or as JSON if needed
                    # (For now they're handled as part of ai_info document field)
                    pass
                    
        # Store complete AI data as JSON for other fields
        # This is a fallback for data not fitting into the structured schema
        self.cursor.execute("""
        INSERT OR REPLACE INTO metadata_json 
        (image_id, section, data) 
        VALUES (?, ?, ?)
        """, (
            image_id, 
            'ai_info', 
            json.dumps(ai_data)
        ))
    
    def _handle_region_metadata(self, image_id: int, region_data: Dict[str, Any]) -> None:
        """
        Handle region metadata
        
        Args:
            image_id: Image ID
            region_data: Region metadata
        """
        # Process faces
        if 'faces' in region_data:
            for face in region_data['faces']:
                # Extract face data
                face_type = face.get('type', 'Face')
                face_name = face.get('name', 'Face')
                
                # Get coordinates
                if 'area' in face:
                    area = face['area']
                    x, y = area.get('x', 0), area.get('y', 0)
                    w, h = area.get('w', 0), area.get('h', 0)
                else:
                    x, y, w, h = 0, 0, 0, 0
                    
                # Store additional data as JSON
                data = json.dumps(face.get('extensions', {}))
                
                # Insert face region
                self.cursor.execute("""
                INSERT INTO regions 
                (image_id, type, name, x, y, w, h, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (image_id, face_type, face_name, x, y, w, h, data))
                
        # Process areas
        if 'areas' in region_data:
            for area in region_data['areas']:
                # Extract area data
                area_type = area.get('type', 'Area')
                area_name = area.get('name', 'Area')
                
                # Get coordinates
                if 'area' in area:
                    area_coords = area['area']
                    x, y = area_coords.get('x', 0), area_coords.get('y', 0)
                    w, h = area_coords.get('w', 0), area_coords.get('h', 0)
                else:
                    x, y = area.get('x', 0), area.get('y', 0)
                    w, h = area.get('w', 0), area.get('h', 0)
                    
                # Store additional data as JSON
                data = json.dumps(area.get('extensions', {}))
                
                # Insert area region
                self.cursor.execute("""
                INSERT INTO regions 
                (image_id, type, name, x, y, w, h, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (image_id, area_type, area_name, x, y, w, h, data))
    
    def _read_basic_metadata(self, image_id: int, result: Dict[str, Any]) -> None:
        """
        Read basic metadata for image
        
        Args:
            image_id: Image ID
            result: Result dictionary to update
        """
        # Get basic fields from images table
        self.cursor.execute("""
        SELECT filename, format, width, height, orientation, title, description, rating,
               created_date, updated_date
        FROM images
        WHERE id = ?
        """, (image_id,))
        
        row = self.cursor.fetchone()
        if row:
            for key in row.keys():
                if row[key] is not None:
                    result['basic'][key] = row[key]
                    
        # Get keywords
        self.cursor.execute("SELECT keyword FROM keywords WHERE image_id = ?", (image_id,))
        keywords = [row['keyword'] for row in self.cursor.fetchall()]
        if keywords:
            result['basic']['keywords'] = keywords
    
    def _read_analysis_metadata(self, image_id: int, result: Dict[str, Any]) -> None:
        """
        Read analysis metadata for image
        
        Args:
            image_id: Image ID
            result: Result dictionary to update
        """
        # Get scores
        self.cursor.execute("""
        SELECT category, metric, value, higher_better, timestamp
        FROM scores
        WHERE image_id = ?
        """, (image_id,))
        
        # Process scores into nested structure
        for row in self.cursor.fetchall():
            category = row['category']
            metric = row['metric']
            
            # Initialize category if needed
            if category not in result['analysis']:
                result['analysis'][category] = {}
                
            # Handle metric with nested structure
            parts = metric.split('.')
            current = result['analysis'][category]
            
            # Build nested structure
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    # Final part, store the value
                    current[part] = {
                        'score': row['value'],
                        'higher_better': bool(row['higher_better']),
                        'timestamp': row['timestamp']
                    }
                else:
                    # Intermediate part, ensure dict exists
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                    
        # Get classifications
        self.cursor.execute("""
        SELECT category, value, confidence, timestamp
        FROM classifications
        WHERE image_id = ?
        """, (image_id,))
        
        for row in self.cursor.fetchall():
            # Store in classification section or create one
            if 'classification' not in result['analysis']:
                result['analysis']['classification'] = {}
                
            result['analysis']['classification'][row['category']] = {
                'value': row['value'],
                'confidence': row['confidence'],
                'timestamp': row['timestamp']
            }
    
    def _read_ai_metadata(self, image_id: int, result: Dict[str, Any]) -> None:
        """
        Read AI metadata for image
        
        Args:
            image_id: Image ID
            result: Result dictionary to update
        """
        # Get AI generation info
        self.cursor.execute("""
        SELECT model, positive_prompt, negative_prompt, sampler, seed, 
               steps, cfg_scale, timestamp
        FROM ai_info
        WHERE image_id = ?
        """, (image_id,))
        
        row = self.cursor.fetchone()
        if row:
            # Create generation structure
            result['ai_info']['generation'] = {}
            gen = result['ai_info']['generation']
            
            # Store non-null fields
            if row['model']:
                gen['model'] = row['model']
            if row['positive_prompt']:
                gen['prompt'] = row['positive_prompt']
            if row['negative_prompt']:
                gen['negative_prompt'] = row['negative_prompt']
            if row['sampler']:
                gen['sampler'] = row['sampler']
            if row['seed']:
                gen['seed'] = row['seed']
            if row['steps']:
                gen['steps'] = row['steps']
            if row['cfg_scale']:
                gen['cfg_scale'] = row['cfg_scale']
            if row['timestamp']:
                gen['timestamp'] = row['timestamp']
                
        # Get complete AI data from JSON storage
        self.cursor.execute("""
        SELECT data FROM metadata_json
        WHERE image_id = ? AND section = 'ai_info'
        """, (image_id,))
        
        row = self.cursor.fetchone()
        if row:
            try:
                ai_data = json.loads(row['data'])
                
                # Merge with existing data (excluding generation already handled)
                for key, value in ai_data.items():
                    if key != 'generation':
                        result['ai_info'][key] = value
            except json.JSONDecodeError:
                pass
    
    def _read_region_metadata(self, image_id: int, result: Dict[str, Any]) -> None:
        """
        Read region metadata for image
        
        Args:
            image_id: Image ID
            result: Result dictionary to update
        """
        # Create regions structure
        result['regions'] = {
            'faces': [],
            'areas': []
        }
        
        # Get all regions
        self.cursor.execute("""
        SELECT type, name, x, y, w, h, data
        FROM regions
        WHERE image_id = ?
        """, (image_id,))
        
        # Process regions
        for row in self.cursor.fetchall():
            region = {
                'type': row['type'],
                'name': row['name'],
                'area': {
                    'x': row['x'],
                    'y': row['y'],
                    'w': row['w'],
                    'h': row['h']
                }
            }
            
            # Add extensions if available
            if row['data']:
                try:
                    extensions = json.loads(row['data'])
                    region['extensions'] = extensions
                except json.JSONDecodeError:
                    pass
                    
            # Add to appropriate list
            if region['type'] == 'Face':
                result['regions']['faces'].append(region)
            else:
                result['regions']['areas'].append(region)
                
        # Add summary data
        result['regions']['summary'] = {
            'face_count': len(result['regions']['faces']),
            'area_count': len(result['regions']['areas'])
        }
    
    def search_images(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search images based on query criteria
        
        Args:
            query: Dictionary of search criteria
            
        Returns:
            list: List of matching image records
        """
        try:
            # Build query
            sql_parts = ["SELECT i.* FROM images i"]
            params = []
            join_tables = set()
            where_clauses = []
            
            # Process score criteria
            if 'scores' in query:
                for idx, (category, metric, op, value) in enumerate(query['scores']):
                    score_alias = f"s{idx}"
                    sql_parts.append(f"JOIN scores {score_alias} ON i.id = {score_alias}.image_id")
                    
                    # Modify to handle nested metrics with dots
                    if '.' in metric:
                        # For metrics like 'blur.score', we need to match just 'blur'
                        metric_parts = metric.split('.')
                        parent_metric = metric_parts[0]
                        where_clauses.append(
                            f"{score_alias}.category = ? AND {score_alias}.metric LIKE ? AND {score_alias}.value {op} ?"
                        )
                        params.extend([category, f"{parent_metric}%", value])
                    else:
                        where_clauses.append(
                            f"{score_alias}.category = ? AND {score_alias}.metric = ? AND {score_alias}.value {op} ?"
                        )
                        params.extend([category, metric, value])
                    
            # Process keyword criteria
            if 'keywords' in query:
                for idx, keyword in enumerate(query['keywords']):
                    kw_alias = f"k{idx}"
                    sql_parts.append(f"JOIN keywords {kw_alias} ON i.id = {kw_alias}.image_id")
                    where_clauses.append(f"{kw_alias}.keyword = ?")
                    params.append(keyword)
                    
            # Process classifications
            if 'classifications' in query:
                for idx, (category, value) in enumerate(query['classifications']):
                    cl_alias = f"c{idx}"
                    sql_parts.append(f"JOIN classifications {cl_alias} ON i.id = {cl_alias}.image_id")
                    where_clauses.append(f"{cl_alias}.category = ? AND {cl_alias}.value = ?")
                    params.extend([category, value])
                    
            # Process AI model
            if 'model' in query:
                sql_parts.append("JOIN ai_info ai ON i.id = ai.image_id")
                where_clauses.append("ai.model = ?")
                params.append(query['model'])
                
            # Process basic criteria
            if 'orientation' in query:
                where_clauses.append("i.orientation = ?")
                params.append(query['orientation'])
                
            if 'has_text' in query:
                where_clauses.append("i.has_text = ?")
                params.append(1 if query['has_text'] else 0)
                
            # Add WHERE clause if needed
            if where_clauses:
                sql_parts.append("WHERE " + " AND ".join(where_clauses))
                
            # Add ORDER BY if specified
            if 'order_by' in query:
                sql_parts.append(f"ORDER BY {query['order_by']}")
                
            # Add LIMIT if specified
            if 'limit' in query:
                sql_parts.append(f"LIMIT {int(query['limit'])}")

            # Log the final SQL query for debugging
            sql = " ".join(sql_parts)
            self.log(f"Generated SQL query: {sql}", level="DEBUG")
            self.log(f"With parameters: {params}", level="DEBUG")            
                
            # Execute query
            self.cursor.execute(sql, params)
            
            # Return results
            return [dict(row) for row in self.cursor.fetchall()]
            
        except Exception as e:
            self.log(f"Search failed: {str(e)}", level="ERROR", error=e)
            return []
    
    def batch_operation(self, operation: str, filepaths: List[str], 
                       data: Optional[Dict[str, Any]] = None) -> Dict[str, bool]:
        """
        Perform batch operation on multiple files
        
        Args:
            operation: Operation type ('read', 'write', 'delete')
            filepaths: List of file paths
            data: Data for write operation
            
        Returns:
            dict: Status for each file
        """
        results = {}
        
        for filepath in filepaths:
            try:
                if operation == 'read':
                    # Read metadata
                    results[filepath] = self.read_metadata(filepath) != {}
                elif operation == 'write' and data:
                    # Write metadata
                    results[filepath] = self.write_metadata(filepath, data)
                elif operation == 'delete':
                    # Delete metadata
                    results[filepath] = self._delete_metadata(filepath)
                else:
                    results[filepath] = False
            except Exception as e:
                self.log(f"Batch operation failed for {filepath}: {str(e)}", level="ERROR", error=e)
                results[filepath] = False
                
        return results
    
    def _delete_metadata(self, filepath: str) -> bool:
        """
        Delete metadata for a file
        
        Args:
            filepath: Path to the file
            
        Returns:
            bool: True if successful
        """
        try:
            # Get image ID
            self.cursor.execute("SELECT id FROM images WHERE filepath = ?", (filepath,))
            row = self.cursor.fetchone()
            if not row:
                return False
                
            image_id = row['id']
            
            # Begin transaction
            self.cursor.execute("BEGIN TRANSACTION")
            
            # Delete from all tables
            self.cursor.execute("DELETE FROM regions WHERE image_id = ?", (image_id,))
            self.cursor.execute("DELETE FROM ai_info WHERE image_id = ?", (image_id,))
            self.cursor.execute("DELETE FROM classifications WHERE image_id = ?", (image_id,))
            self.cursor.execute("DELETE FROM keywords WHERE image_id = ?", (image_id,))
            self.cursor.execute("DELETE FROM scores WHERE image_id = ?", (image_id,))
            self.cursor.execute("DELETE FROM metadata_json WHERE image_id = ?", (image_id,))
            self.cursor.execute("DELETE FROM images WHERE id = ?", (image_id,))
            
            # Commit transaction
            self.conn.commit()
            
            return True
            
        except Exception as e:
            # Rollback transaction
            self.conn.rollback()
            self.log(f"Delete failed: {str(e)}", level="ERROR", error=e)
            return False
    
    def cleanup(self) -> None:
        """Clean up database connection"""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
                self.cursor = None
                self.log("Database connection closed", level="DEBUG")
        except Exception as e:
            self.log(f"Cleanup error: {str(e)}", level="ERROR", error=e)
    
    def close(self) -> None:
        """Close database connection (alias for cleanup)"""
        self.cleanup()
    
    def __del__(self) -> None:
        """Ensure cleanup on deletion"""
        self.cleanup()