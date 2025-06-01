"""
Database service for the Ski Season Planner application.
Handles SQLite database operations, initialization, and queries.
"""
import os
import sqlite3
import json
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for handling SQLite database operations."""
    
    def __init__(self, db_path="data/ski_planner.db"):
        """
        Initialize the database service.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize the database
        self.initialize_db()
    
    def initialize_db(self):
        """Initialize the database with required tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create stations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            region TEXT,
            base_altitude INTEGER,
            top_altitude INTEGER,
            vertical_drop INTEGER,
            total_pistes_km REAL,
            easy_km REAL,
            intermediate_km REAL,
            difficult_km REAL,
            lifts INTEGER,
            location TEXT,
            additional_info TEXT,
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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stations_location ON stations(location)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stations_name ON stations(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stations_region ON stations(region)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stations_pistes ON stations(total_pistes_km)')
        
        conn.commit()
        conn.close()
        
        logger.info("Database initialized successfully")
    
    def _get_connection(self):
        """Get a connection to the SQLite database."""
        return sqlite3.connect(self.db_path)
    
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
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            count = 0
            for station in data.get('stations', []):
                # Extract difficulty breakdown
                difficulty = station.get('difficulty_breakdown', {})
                
                # Convert any additional fields to JSON string
                additional_info = {}
                for key, value in station.items():
                    if key not in ['name', 'region', 'base_altitude', 'top_altitude', 
                                  'vertical_drop', 'total_pistes_km', 'difficulty_breakdown',
                                  'lifts', 'location']:
                        additional_info[key] = value
                
                # Use the region as location if location is not provided
                location = station.get('region', '')
                
                cursor.execute('''
                INSERT OR REPLACE INTO stations 
                (name, region, base_altitude, top_altitude, vertical_drop, 
                total_pistes_km, easy_km, intermediate_km, difficult_km, 
                lifts, location, additional_info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    station.get('name'),  # Name is required
                    station.get('region'),
                    station.get('base_altitude'),
                    station.get('top_altitude'),
                    station.get('vertical_drop'),
                    station.get('total_pistes_km'),
                    difficulty.get('easy_km'),
                    difficulty.get('intermediate_km'),
                    difficulty.get('difficult_km'),
                    station.get('lifts'),
                    location,
                    json.dumps(additional_info)
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
            INSERT INTO distances (origin, destination, transport_mode, distance, duration)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(origin, destination, transport_mode) 
            DO UPDATE SET distance = ?, duration = ?, timestamp = CURRENT_TIMESTAMP
            """,
            (origin, destination, transport_mode, distance, duration, distance, duration)
        )
        
        conn.commit()
        conn.close()
    
    def check_origin_calculated(self, origin: str, transport_mode: str) -> bool:
        """
        Check if distances from this origin have been calculated.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            
        Returns:
            bool: True if the origin has been fully calculated, False otherwise
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT transport_modes, complete FROM calculated_origins WHERE origin = ?",
            (origin,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        transport_modes = result[0].split(',')
        is_complete = result[1]
        
        return transport_mode in transport_modes and is_complete
    
    def mark_origin_calculated(self, origin: str, transport_mode: str, complete: bool = True):
        """
        Mark an origin as having calculated distances.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            complete: Whether all stations have been calculated
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if entry exists
        cursor.execute("SELECT transport_modes FROM calculated_origins WHERE origin = ?", (origin,))
        result = cursor.fetchone()
        
        if result:
            # Update existing entry
            current_modes = set(result[0].split(','))
            current_modes.add(transport_mode)
            modes_str = ','.join(current_modes)
            
            cursor.execute(
                "UPDATE calculated_origins SET transport_modes = ?, complete = ?, last_updated = CURRENT_TIMESTAMP WHERE origin = ?",
                (modes_str, complete, origin)
            )
        else:
            # Create new entry
            cursor.execute(
                "INSERT INTO calculated_origins (origin, transport_modes, complete) VALUES (?, ?, ?)",
                (origin, transport_mode, complete)
            )
        
        conn.commit()
        conn.close()
    
    def get_all_destinations_with_distances(self, origin: str, transport_mode: str) -> List[str]:
        """
        Get all destinations that have distance data for a given origin and transport mode.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            
        Returns:
            List of destination locations
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT destination FROM distances WHERE origin = ? AND transport_mode = ?",
            (origin, transport_mode)
        )
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return results
    
    # Station query methods
    
    def get_all_stations(self) -> List[Dict[str, Any]]:
        """
        Get all stations from the database.
        
        Returns:
            List of station dictionaries
        """
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM stations")
        results = [dict(row) for row in cursor.fetchall()]
        
        # Parse additional_info JSON and format for Station model
        for station in results:
            if station['additional_info']:
                additional_info = json.loads(station['additional_info'])
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
        
        conn.close()
        return results
    
    def get_closest_stations(self, origin: str, transport_mode: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the closest stations to an origin location.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            limit: Maximum number of results
            
        Returns:
            List of station dictionaries with distance information
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
            LIMIT ?
            """,
            (origin, transport_mode, limit)
        )
        results = [dict(row) for row in cursor.fetchall()]
        
        # Parse additional_info JSON and format for Station model
        for station in results:
            if station['additional_info']:
                additional_info = json.loads(station['additional_info'])
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
        
        conn.close()
        return results
    
    def get_stations_by_date(self, origin: str, transport_mode: str, date: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get stations open on a specific date, sorted by distance.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            date: Date in format YYYY-MM-DD
            limit: Maximum number of results
            
        Returns:
            List of station dictionaries with distance information
        """
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Note: Since we don't have season_start and season_end in our new schema,
        # we'll just return all stations sorted by distance for now
        cursor.execute(
            """
            SELECT s.*, d.distance, d.duration 
            FROM stations s
            JOIN distances d ON s.name = d.destination
            WHERE d.origin = ? AND d.transport_mode = ?
            ORDER BY d.distance ASC
            LIMIT ?
            """,
            (origin, transport_mode, limit)
        )
        results = [dict(row) for row in cursor.fetchall()]
        
        # Parse additional_info JSON and format for Station model
        for station in results:
            if station['additional_info']:
                additional_info = json.loads(station['additional_info'])
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
        
        conn.close()
        return results
    
    def get_stations_by_piste_length(self, origin: str, transport_mode: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get stations sorted by piste length and then by distance.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            limit: Maximum number of results
            
        Returns:
            List of station dictionaries with distance information
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
            ORDER BY s.total_pistes_km DESC, d.distance ASC
            LIMIT ?
            """,
            (origin, transport_mode, limit)
        )
        results = [dict(row) for row in cursor.fetchall()]
        
        # Parse additional_info JSON and format for Station model
        for station in results:
            if station['additional_info']:
                additional_info = json.loads(station['additional_info'])
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
        
        conn.close()
        return results
        
    def get_all_stations_with_distances(self, origin: str, transport_mode: str) -> List[Dict[str, Any]]:
        """
        Get all stations with their distances from an origin.
        
        Args:
            origin: Origin location
            transport_mode: Mode of transport
            
        Returns:
            List of station dictionaries with distance information
        """
        conn = self._get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT s.name, s.region, s.total_pistes_km, s.base_altitude, s.top_altitude,
                   d.distance, d.duration 
            FROM stations s
            JOIN distances d ON s.name = d.destination
            WHERE d.origin = ? AND d.transport_mode = ?
            ORDER BY d.distance ASC
            """,
            (origin, transport_mode)
        )
        results = [dict(row) for row in cursor.fetchall()]
        
        # Parse additional_info JSON and format for Station model
        for station in results:
            if 'additional_info' in station and station['additional_info']:
                additional_info = json.loads(station['additional_info'])
                station.update(additional_info)
        
        conn.close()
        return results
