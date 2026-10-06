"""Shared lists. Add new vehicle types here (admin page can also add at runtime)."""
VEHICLE_TYPES = ["Tractor", "Harvester", "Combine Harvester", "Rotavator", "Cultivator",
                 "Seed Drill", "Plough", "Thresher", "Sprayer", "Tiller", "Trailer",
                 "Paddy Transplanter", "Other"]
CROPS = ["Paddy", "Cotton", "Maize", "Chilli", "Groundnut", "Sugarcane", "Wheat", "Turmeric"]
ACTIVITIES = ["Ploughing", "Tilling", "Sowing", "Transplanting", "Spraying", "Harvesting",
              "Threshing", "Transport"]
# Which vehicle types can do which activity (used by recommender + synthetic data)
ACTIVITY_VEHICLES = {
    "Ploughing": ["Tractor", "Plough", "Cultivator"],
    "Tilling": ["Rotavator", "Tiller", "Cultivator", "Tractor"],
    "Sowing": ["Seed Drill", "Tractor"],
    "Transplanting": ["Paddy Transplanter", "Tractor"],
    "Spraying": ["Sprayer", "Tractor"],
    "Harvesting": ["Combine Harvester", "Harvester"],
    "Threshing": ["Thresher"],
    "Transport": ["Trailer", "Tractor"],
}
# Crop -> activities that are typical
CROP_ACTIVITIES = {
    "Paddy": ["Ploughing", "Tilling", "Transplanting", "Harvesting", "Threshing"],
    "Cotton": ["Ploughing", "Sowing", "Spraying", "Transport"],
    "Maize": ["Ploughing", "Sowing", "Harvesting", "Threshing"],
    "Chilli": ["Tilling", "Spraying", "Transport"],
    "Groundnut": ["Ploughing", "Sowing", "Harvesting"],
    "Sugarcane": ["Ploughing", "Tilling", "Harvesting", "Transport"],
    "Wheat": ["Ploughing", "Sowing", "Harvesting", "Threshing"],
    "Turmeric": ["Tilling", "Sowing", "Transport"],
}
# Demo locations (Andhra Pradesh / Telangana) with lat, lon
LOCATIONS = {
    "Guntur": (16.3067, 80.4365), "Vijayawada": (16.5062, 80.6480),
    "Tenali": (16.2430, 80.6400), "Narasaraopet": (16.2350, 80.0490),
    "Ongole": (15.5057, 80.0499), "Eluru": (16.7107, 81.0952),
    "Machilipatnam": (16.1875, 81.1389), "Nellore": (14.4426, 79.9865),
    "Kurnool": (15.8281, 78.0373), "Warangal": (17.9689, 79.5941),
    "Khammam": (17.2473, 80.1514), "Hyderabad": (17.3850, 78.4867),
}
def season_of(month: int) -> str:
    return "Kharif" if month in (6, 7, 8, 9, 10) else "Rabi" if month in (11, 12, 1, 2, 3) else "Summer"
