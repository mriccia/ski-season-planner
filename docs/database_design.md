# Ski Season Planner Database Design Document

## Overview
This document outlines the database design for the Ski Season Planner application. The database uses SQLite to store information about ski resorts, distance calculations, and calculation status to optimize performance and reduce API calls.

## Database Schema

### 1. Stations Table
Stores information about ski resorts/stations.

```sql
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
```

### 2. Distances Table
Stores distance and duration information between origins (user locations) and destinations (ski stations).

```sql
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
```

### 3. Calculated Origins Table
Tracks which cities (origins) have had their distances calculated.

```sql
CREATE TABLE IF NOT EXISTS calculated_origins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin TEXT NOT NULL UNIQUE,
    transport_modes TEXT NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    complete BOOLEAN DEFAULT 0
)
```

## Indexes
To optimize query performance, the following indexes are created:

```sql
CREATE INDEX IF NOT EXISTS idx_distances_origin ON distances(origin, transport_mode)
CREATE INDEX IF NOT EXISTS idx_distances_destination ON distances(destination)
CREATE INDEX IF NOT EXISTS idx_stations_name ON stations(name)
CREATE INDEX IF NOT EXISTS idx_stations_region ON stations(region)
CREATE INDEX IF NOT EXISTS idx_stations_pistes ON stations(total_pistes_km)
CREATE INDEX IF NOT EXISTS idx_stations_coordinates ON stations(longitude, latitude)
CREATE INDEX IF NOT EXISTS idx_stations_magic_pass_url ON stations(magic_pass_url)
```

## Common Queries

### 1. Check if distances for a city have been calculated
```sql
SELECT complete, transport_modes 
FROM calculated_origins 
WHERE origin = ?;
```

### 2. Get closest resorts for a city
```sql
SELECT s.name, s.region, s.total_pistes_km, s.magic_pass_url, d.distance, d.duration 
FROM stations s
JOIN distances d ON s.name = d.destination
WHERE d.origin = ? AND d.transport_mode = ?
ORDER BY d.distance ASC;
```

### 3. Get resorts sorted by piste length
```sql
SELECT s.name, s.region, s.total_pistes_km, s.magic_pass_url, d.distance, d.duration 
FROM stations s
JOIN distances d ON s.name = d.destination
WHERE d.origin = ? AND d.transport_mode = ?
ORDER BY s.total_pistes_km DESC, d.distance ASC;
```

### 4. Get resorts with specific criteria
```sql
SELECT s.name, s.region, s.total_pistes_km, s.vertical_drop, s.magic_pass_url, d.distance, d.duration 
FROM stations s
JOIN distances d ON s.name = d.destination
WHERE d.origin = ? 
  AND d.transport_mode = ?
  AND s.total_pistes_km > ?
  AND s.vertical_drop > ?
ORDER BY d.distance ASC;
```

## Data Migration
Initial data for the stations table is migrated from the existing `magic_pass_stations.json` file. This is done during the first application run through the `database_service.py` module.

## Database Service Interface
The application interacts with the database through a `DatabaseService` class that provides methods for:

1. **Initialization**:
   - `__init__(self)`: Initialize the database connection using the configured DB_FILE_PATH
   - `initialize_db(self)`: Create tables and indexes if they don't exist

2. **Station Operations**:
   - `import_stations_from_json(self, json_data)`: Import stations from JSON data
   - `get_all_stations(self)`: Get all stations from the database
   - `get_station_by_name(self, name)`: Get a station by name
   - `get_stations_by_region(self, region)`: Get stations by region

3. **Distance Operations**:
   - `save_distance(self, origin, destination, transport_mode, distance, duration)`: Save distance calculation
   - `get_distance(self, origin, destination, transport_mode)`: Get distance between two locations
   - `get_all_distances(self, origin, transport_mode)`: Get all distances from an origin
   - `mark_origin_calculated(self, origin, transport_mode, complete=True)`: Mark an origin as calculated
   - `is_origin_calculated(self, origin, transport_mode)`: Check if an origin has been calculated

## Performance Considerations
1. The database is used to cache distance calculations to reduce API calls
2. Queries are optimized to use indexes for faster retrieval
3. The calculated_origins table provides quick lookup to determine if calculations are needed
4. Parallel processing is used for distance calculations with ThreadPoolExecutor
5. Retry mechanism with exponential backoff is implemented for API calls

## Future Enhancements
1. **User Preferences Table**: Store user preferences across sessions
   ```sql
   CREATE TABLE user_preferences (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       user_id TEXT NOT NULL UNIQUE,
       home_location TEXT,
       transport_mode TEXT,
       criteria TEXT,  -- JSON string of criteria
       priorities TEXT -- JSON string of priorities
   );
   ```

2. **Trips Table**: Store planned trips
   ```sql
   CREATE TABLE trips (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       user_id TEXT NOT NULL,
       start_date TEXT NOT NULL,
       end_date TEXT NOT NULL,
       criteria TEXT,  -- JSON string of criteria
       priorities TEXT -- JSON string of priorities
   );
   ```

3. **Data Refresh Mechanism**: Implement automatic refresh for outdated distance calculations
4. **Version Tracking**: Add version tracking for schema changes
5. **Migration System**: Create a migration system for future schema updates
6. **Performance Metrics**: Add logging for performance monitoring

## MCP Integration
The database can be accessed through the Claude MCP SQLite server, allowing the Agent Service to query the database directly. See the `mcp_usage.md` document for details on setting up and using the MCP server with this database.
