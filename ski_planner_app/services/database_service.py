"""
Database service for the Ski Season Planner application.
Handles SQLite database operations, initialization, and queries.
"""
import os
import sqlite3
import json
from typing import Dict, List, Any, Optional, Tuple
import logging
from ski_planner_app.config import DB_FILE_PATH

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for handling SQLite database operations."""
    
    def __init__(self):
        """
        Initialize the database service.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = DB_FILE_PATH
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize the database
        self.initialize_db()
    
    def initialize_db(self):
        """Initialize the database with required tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create stations table with flattened structure
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            region TEXT,
            base_altitude INTEGER,
            top_altitude INTEGER,
            vertical_drop INTEGER,
            total_pistes_km REAL,
            longitude REAL,
            latitude REAL,
            magic_pass_url TEXT,
            UNIQUE(name)
        )
        ''')
        
        # Create distances table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS distances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            transport_mode TEXT NOT NULL,
            distance REAL NOT NULL,
            duration REAL NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(origin, destination, transport_mode)
        )
        ''')
        
        # Create calculated_origins table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS calculated_origins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT NOT NULL UNIQUE,
            transport_modes TEXT NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            complete BOOLEAN DEFAULT 0
        )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_distances_origin ON distances(origin, transport_mode)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_distances_destination ON distances(destination)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stations_name ON stations(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stations_region ON stations(region)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stations_pistes ON stations(total_pistes_km)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stations_coordinates ON stations(longitude, latitude)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stations_magic_pass_url ON stations(magic_pass_url)')
        
        conn.commit()
        conn.close()
        
        logger.info("Database initialized successfully")
    
    def _get_connection(self):
        """Get a connection to the SQLite database."""
        return sqlite3.connect(self.db_path)
    
    def _process_station_result(self, station):
        """
        Process a station result from the database query.
        
        Args:
            station: Dictionary containing station data from the database
            
        Returns:
            Dict: Processed station dictionary
        """
        # Parse additional_info JSON
        if station['additional_info']:
            additional_info = json.loads(station['additional_info'])
            
            # Extract coordinates if available
            if 'coordinates' in additional_info:
                station['coordinates'] = additional_info['coordinates']
                # Remove coordinates from additional_info to avoid duplication
                additional_info_without_coords = {k: v for k, v in additional_info.items() if k != 'coordinates'}
                station.update(additional_info_without_coords)
            else:
                station.update(additional_info)
        
        # Format difficulty breakdown for Station model
        station['difficulty_breakdown'] = {
            'easy_km': station.get('easy_km', 0),
            'intermediate_km': station.get('intermediate_km', 0),
            'difficult_km': station.get('difficult_km', 0)
        }
        
        # Remove individual difficulty fields to avoid duplication
        station.pop('easy_km', None)
        station.pop('intermediate_km', None)
        station.pop('difficult_km', None)
        
        return station
    
    def import_stations_from_json(self, json_path):
        """
        Import stations data from JSON file to SQLite database.
        
        Args:
            json_path: Path to the JSON file containing station data
        
        Returns:
            int: Number of stations imported
        """
        if not os.path.exists(json_path):
            logger.error(f"JSON file not found: {json_path}")
            return 0
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            count = 0
            for station in data.get('stations', []):
                cursor.execute('''
                INSERT OR REPLACE INTO stations 
                (name, region, base_altitude, top_altitude, vertical_drop, 
                total_pistes_km, longitude, latitude, magic_pass_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    station.get('name'),  # Name is required
                    station.get('region'),
                    station.get('base_altitude'),
                    station.get('top_altitude'),
                    station.get('vertical_drop'),
                    station.get('total_pistes_km'),
                    station.get('longitude'),
                    station.get('latitude'),
                    f"https://www.magicpass.ch/en/ski-resorts/{station['mp_station_id']}"
                ))
                count += 1
            
            conn.commit()
            conn.close()
            
            logger.info(f"Imported {count} stations from JSON")
            return count
            
        except Exception as e:
            logger.error(f"Error importing stations from JSON: {e}")
            return 0
    
    def is_stations_table_populated(self):
        """
        Check if the stations table has data.
        
        Returns:
            bool: True if the table has at least one record, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM stations")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count > 0
    
    # Distance-related methods
    
    def get_distance(self, origin: str, destination: str, transport_mode: str) -> Optional[Dict[str, Any]]:
        """
        Get distance data from the database if it exists.
        
        Args:
            origin: Origin location
            destination: Destination location
            transport_mode: Mode of transport
            
        Returns:
            Dict with distance and duration if found, None otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT distance, duration FROM distances WHERE origin = ? AND destination = ? AND transport_mode = ?",
            (origin, destination, transport_mode)
        )
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return {
                "distance": result[0],
                "duration": result[1]
            }
        return None
    
    def save_distance(self, origin: str, destination: str, transport_mode: str, distance: float, duration: float):
        """
        Save distance data to the database.
        
        Args:
            origin: Origin location
            destination: Destination location
            transport_mode: Mode of transport
            distance: Distance in kilometers
            duration: Duration in minutes
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT OR REPLACE INTO distances 
            (origin, destination, transport_mode, distance, duration) 
            VALUES (?, ?, ?, ?, ?)
            """,
            (origin, destination, transport_mode, distance, duration)
        )
        
        conn.commit()
        conn.close()
    
    def mark_origin_calculated(self, origin: str, transport_mode: str, complete: bool = True):
        """
        Mark an origin as having all its distances calculated.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            complete: Whether all destinations have been calculated
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT OR REPLACE INTO calculated_origins 
            (origin, transport_modes, complete) 
            VALUES (?, ?, ?)
            """,
            (origin, transport_mode, complete)
        )
        
        conn.commit()
        conn.close()
    
    def check_origin_calculated(self, origin: str, transport_mode: str) -> bool:
        """
        Check if an origin has been marked as calculated.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            
        Returns:
            bool: True if the origin has been calculated, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT complete FROM calculated_origins WHERE origin = ? AND transport_modes = ?",
            (origin, transport_mode)
        )
        result = cursor.fetchone()
        
        conn.close()
        
        return result is not None and result[0] == 1
    
    def get_all_destinations_with_distances(self, origin: str, transport_mode: str) -> List[str]:
        """
        Get all destinations that have distances calculated from an origin.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            
        Returns:
            List[str]: List of destination names
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT destination FROM distances WHERE origin = ? AND transport_mode = ?",
            (origin, transport_mode)
        )
        results = cursor.fetchall()
        
        conn.close()
        
        return [result[0] for result in results]
    
    def get_all_stations(self) -> List[Dict[str, Any]]:
        """
        Get all stations from the database.
        
        Returns:
            List[Dict]: List of station dictionaries
        """
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM stations")
        results = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_all_stations_with_distances(self, origin: str, transport_mode: str) -> List[Dict[str, Any]]:
        """
        Get all stations with their distances from an origin.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            
        Returns:
            List[Dict]: List of station dictionaries with distance information
        """
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT s.*, d.distance, d.duration 
            FROM stations s
            JOIN distances d ON s.name = d.destination
            WHERE d.origin = ? AND d.transport_mode = ?
            ORDER BY d.distance ASC
            """,
            (origin, transport_mode)
        )
        results = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return results
    