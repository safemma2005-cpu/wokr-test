from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from database import engine

app = FastAPI()

# Разрешаем React подключаться
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "Taxi Dashboard API works"}

@app.get("/revenue")
def revenue(tariff: str = "All"):

    query = """
        SELECT
            DATE(t.created_at) AS day,
            SUM(t.price) AS revenue
        FROM trips t
        JOIN tariffs ta ON ta.tariff_id = t.tariff_id
        WHERE t.status = 'finished'
    """

    if tariff != "All":
        query += " AND ta.description = :tariff "

    query += """
        GROUP BY day
        ORDER BY day;
    """

    with engine.connect() as conn:
        result = conn.execute(text(query), {"tariff": tariff})
        return [dict(r._mapping) for r in result]

    
@app.get("/driver-revenue")
def driver_revenue(tariff: str = "All"):

    query = """
        SELECT
            d.name,
            COUNT(*) AS trips,
            SUM(t.price) AS revenue,
            d.rating
        FROM trips t
        JOIN drivers d
            ON d.driver_id = t.driver_id
        JOIN tariffs ta
            ON ta.tariff_id = t.tariff_id
        WHERE t.status = 'finished'
    """

    if tariff != "All":
        query += " AND ta.description = :tariff "

    query += """
        GROUP BY d.name, d.rating
        ORDER BY revenue DESC
        LIMIT 20;
    """

    with engine.connect() as conn:
        result = conn.execute(
            text(query),
            {"tariff": tariff}
        )
        rows = [
            dict(r._mapping)
            for r in result
        ]

    return rows
    
@app.get("/tariff-revenue")
def tariff_revenue():

    query = """
        SELECT
            ta.description AS tariff,
            SUM(t.price) AS revenue,
            COUNT(*) AS trips
        FROM trips t
        JOIN tariffs ta ON ta.tariff_id = t.tariff_id
        WHERE t.status = 'finished'
        GROUP BY ta.description
        ORDER BY revenue DESC;
    """

    with engine.connect() as conn:
        result = conn.execute(text(query))
        return [dict(r._mapping) for r in result]

@app.get("/tariffs")
def tariffs():

    query = """
        SELECT
            ta.description,
            COUNT(*) as trips
        FROM trips t
        JOIN tariffs ta
        ON ta.tariff_id=t.tariff_id
        GROUP BY ta.description
    """

    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = [dict(r._mapping) for r in result]

    return rows

@app.get("/drivers")
def drivers():

    query = """
        SELECT
            name,
            rating
        FROM drivers
        LIMIT 10
    """

    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = [dict(r._mapping) for r in result]

    return rows

@app.get("/kpi")
def kpi(tariff: str = "All"):

    query = """
        SELECT
            COUNT(*) AS total_trips,
            SUM(CASE WHEN status='finished' THEN price ELSE 0 END) AS total_revenue,
            AVG(CASE WHEN status='finished' THEN price END) AS avg_fare,
            AVG(d.rating) AS avg_driver_rating,
            AVG(EXTRACT(EPOCH FROM (t.finished_at - t.created_at)) / 60) AS avg_trip_minutes,
            100.0 * SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END) / COUNT(*) AS cancel_rate
        FROM trips t
        LEFT JOIN drivers d ON d.driver_id = t.driver_id
        JOIN tariffs ta ON ta.tariff_id = t.tariff_id
        WHERE t.status IN ('finished', 'cancelled')
    """

    if tariff != "All":
        query += " AND ta.description = :tariff "

    with engine.connect() as conn:
        result = conn.execute(text(query), {"tariff": tariff})
        return dict(result.fetchone()._mapping)

@app.get("/hourly")
def hourly(tariff: str = "All"):

    query = """
        SELECT
            EXTRACT(HOUR FROM created_at) AS hour,
            CASE
                WHEN EXTRACT(DOW FROM created_at) IN (0,6)
                THEN 'weekend'
                ELSE 'weekday'
            END AS day_type,
            COUNT(*) AS trips
        FROM trips t
        JOIN tariffs ta
            ON ta.tariff_id = t.tariff_id
        WHERE t.status = 'finished'
    """

    if tariff != "All":
        query += " AND ta.description = :tariff "

    query += """
        GROUP BY hour, day_type
        ORDER BY hour;
    """

    with engine.connect() as conn:
        result = conn.execute(text(query), {"tariff": tariff})
        return [dict(r._mapping) for r in result]

@app.get("/price-boxplot")
def price_boxplot(tariff: str = "All"):

    query = """
        SELECT
            ta.description,
            t.price
        FROM trips t
        JOIN tariffs ta
        ON ta.tariff_id = t.tariff_id
        WHERE t.status='finished';
    """
    if tariff != "All":
        query += " AND ta.description = :tariff "

    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = [dict(r._mapping) for r in result]

    return rows

@app.get("/top-drivers")
def top_drivers(tariff: str = "All"):

    query = """
        SELECT
            d.name,
            COUNT(*) AS trips,
            SUM(t.price) AS revenue,
            AVG(d.rating) AS rating
        FROM drivers d
        JOIN trips t ON d.driver_id = t.driver_id
        JOIN tariffs ta ON ta.tariff_id = t.tariff_id
        WHERE t.status = 'finished'
    """

    if tariff != "All":
        query += " AND ta.description = :tariff "

    query += """
        GROUP BY d.name
        ORDER BY revenue DESC
        LIMIT 10;
    """

    with engine.connect() as conn:
        result = conn.execute(text(query), {"tariff": tariff})
        return [dict(r._mapping) for r in result]

@app.get("/heatmap")
def heatmap(tariff: str = "All"):

    query = """
        SELECT
            EXTRACT(DOW FROM created_at) AS weekday,
            EXTRACT(HOUR FROM created_at) AS hour,
            COUNT(*) AS trips
        FROM trips t
        JOIN tariffs ta
            ON ta.tariff_id = t.tariff_id
        WHERE t.status = 'finished'
    """

    if tariff != "All":
        query += " AND ta.description = :tariff "

    query += """
        GROUP BY weekday, hour
        ORDER BY weekday, hour;
    """

    with engine.connect() as conn:
        result = conn.execute(text(query), {"tariff": tariff})
        return [dict(r._mapping) for r in result]

@app.get("/map")
def trip_map():

    query = """
        SELECT
            pickup_lat,
            pickup_lng,
            dropoff_lat,
            dropoff_lng
        FROM trips
        WHERE pickup_lat IS NOT NULL
        LIMIT 100;
    """

    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = [dict(r._mapping) for r in result]

    return rows

@app.get("/pareto")
def pareto():

    query = """
        SELECT
            d.name,
            ta.description AS tariff,
            SUM(t.price) AS revenue
        FROM trips t
        JOIN drivers d
            ON d.driver_id = t.driver_id
        JOIN tariffs ta
            ON ta.tariff_id = t.tariff_id
        WHERE t.status = 'finished'
        GROUP BY d.name, ta.description
        ORDER BY revenue DESC;
    """

    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = [dict(r._mapping) for r in result]

    return rows