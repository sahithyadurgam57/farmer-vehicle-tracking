"""AgriConnect AI - Streamlit app.

Run:
    streamlit run app.py
"""

import os
import datetime as dt

import pandas as pd
import streamlit as st

from core import db, auth, pricing, recommend, suggest, assistant
from core.constants import CROPS, ACTIVITIES, LOCATIONS, VEHICLE_TYPES


# ---------------------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AgriConnect AI",
    page_icon="🚜",
    layout="wide",
)


# ---------------------------------------------------------------------------
# DATABASE / ML INITIALIZATION
# ---------------------------------------------------------------------------

db.init_db()

# Seed database if there are no users.
try:
    has_users = bool(db.q("SELECT 1 FROM users LIMIT 1"))
except Exception:
    has_users = False

if not has_users:
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, "seed.py"],
        check=False,
    )

# Train price model if it doesn't exist.
price_model_path = os.path.join(
    pricing.ML,
    "price_model.joblib",
)

if not os.path.exists(price_model_path):
    import subprocess
    import sys

    subprocess.run(
        [sys.executable, "ml/train_price_model.py"],
        check=False,
    )


# ---------------------------------------------------------------------------
# CUSTOM CSS
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .hero {
        background: linear-gradient(135deg, #2E7D32, #9CCC65);
        color: #fff;
        padding: 2.2rem;
        border-radius: 20px;
        margin-bottom: 1rem;
    }

    .hero h1 {
        color: #fff;
        margin: 0;
    }

    .card {
        background: #F1F8E9;
        border: 1px solid #C5E1A5;
        border-radius: 16px;
        padding: 1rem;
        margin-bottom: .8rem;
    }

    .badge {
        background: #FFF59D;
        border-radius: 10px;
        padding: 2px 8px;
        margin-right: 6px;
        font-size: .85rem;
    }

    .stButton > button {
        border-radius: 12px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------

ss = st.session_state

# IMPORTANT:
# These are initialized BEFORE any page function can access them.
ss.setdefault("user", None)
ss.setdefault("req", None)
ss.setdefault("res", [])
ss.setdefault("loc", None)
ss.setdefault("price", None)
ss.setdefault("chat", [])


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

STATUS_ICON = {
    "Available": "🟢",
    "Busy": "🟡",
    "Maintenance": "🔴",
    "Offline": "🔴",
}


def logout():
    """Clear the current Streamlit session."""
    st.session_state.clear()


def bar(label, value):
    """Display a percentage progress bar safely."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0

    value = min(max(value, 0), 100)

    st.progress(
        value / 100,
        text=f"{label}: {value:.0f}%",
    )


# ---------------------------------------------------------------------------
# LANDING / AUTH
# ---------------------------------------------------------------------------

def landing():
    st.markdown(
        """
        <div class='hero'>
            <h1>🚜 AgriConnect AI</h1>
            <h3>Find the Right Agricultural Vehicle Near You</h3>
            <p>
                AI-powered vehicle recommendations, smart price prediction
                and easy booking for farmers.
                <br>
                <i>The Right Vehicle. The Right Price. At the Right Time.</i>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns([3, 2])

    with c1:
        st.subheader("How it works")

        steps = [
            "Tell us what you need",
            "AI finds suitable vehicles",
            "Compare prices and distance",
            "Book your vehicle",
            "Complete your farming work",
        ]

        for i, text in enumerate(steps, 1):
            st.write(f"**{i}.** {text}")

        st.subheader("Why choose us?")

        st.write(
            "🤖 AI Vehicle Recommendation  •  "
            "💰 Smart Price Prediction  •  "
            "📍 Nearby Vehicle Search  •  "
            "🔎 Transparent Pricing  •  "
            "📅 Easy Booking  •  "
            "✅ Verified Vehicle Owners"
        )

        st.info(
            "Demo logins (sample data): "
            "farmer@demo.com, owner@demo.com, admin@demo.com "
            "— password Demo@123"
        )

    with c2:
        tab1, tab2 = st.tabs(["Login", "Register"])

        # ------------------------------------------------------------------
        # LOGIN
        # ------------------------------------------------------------------

        with tab1:
            email = st.text_input(
                "Email",
                key="login_email",
            )

            password = st.text_input(
                "Password",
                type="password",
                key="login_password",
            )

            if st.button(
                "Login",
                type="primary",
                use_container_width=True,
                key="login_button",
            ):
                user = auth.login(email, password)

                if user:
                    ss.user = user

                    # Clear old search state when a new user logs in.
                    ss.req = None
                    ss.res = []
                    ss.loc = None
                    ss.price = None
                    ss.chat = []

                    st.rerun()

                else:
                    st.error("Wrong email or password.")

        # ------------------------------------------------------------------
        # REGISTER
        # ------------------------------------------------------------------

        with tab2:
            role = st.radio(
                "I am a",
                ["Farmer", "Vehicle Owner"],
                horizontal=True,
                key="register_role",
            )

            name = st.text_input(
                "Full name",
                key="register_name",
            )

            phone = st.text_input(
                "Phone",
                key="register_phone",
            )

            email = st.text_input(
                "Email",
                key="register_email",
            )

            password = st.text_input(
                "Password (min 6 chars)",
                type="password",
                key="register_password",
            )

            location = st.selectbox(
                "Your town",
                list(LOCATIONS),
                key="register_location",
            )

            if st.button(
                "Create account",
                use_container_width=True,
                key="register_button",
            ):
                if not name.strip():
                    st.error("Please enter your name.")

                else:
                    user_role = (
                        "farmer"
                        if role == "Farmer"
                        else "owner"
                    )

                    uid, error = auth.register(
                        name.strip(),
                        phone,
                        email,
                        password,
                        user_role,
                        location,
                        *LOCATIONS[location],
                    )

                    if error:
                        st.error(error)

                    else:
                        message = "Account created! Please login."

                        if role != "Farmer":
                            message += (
                                " Admin must verify owner accounts "
                                "before vehicles are shown."
                            )

                        st.success(message)


# ---------------------------------------------------------------------------
# FARMER - VEHICLE CARD
# ---------------------------------------------------------------------------

def vehicle_card(vehicle, user_id, key):
    rating = vehicle.get("rating")

    rating_text = rating if rating else "New"

    badges = "".join(
        f"<span class='badge'>{badge}</span>"
        for badge in vehicle.get("badges", [])
    )

    status = vehicle.get(
        "availability_status",
        "Offline",
    )

    status_icon = STATUS_ICON.get(
        status,
        "🔴",
    )

    st.markdown(
        f"""
        <div class='card'>
            <b>
                🚜 {vehicle['brand']} {vehicle['model']}
            </b>
            ({vehicle['vehicle_type']})
            &nbsp;
            {badges}
            <br>
            ⭐ {rating_text}
            ({vehicle['reviews']})
            &nbsp;
            📍 {vehicle['distance_km']} km
            (~{vehicle['travel_min']} min)
            &nbsp;
            💰 ₹{vehicle['price_per_day']:,.0f}/day
            &nbsp;
            {status_icon} {status}
            &nbsp;
            ⚡ {vehicle['horsepower']} HP
            <br>
            <b>AI Match: {vehicle['score']}%</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Why this match? / score details"):
        st.write(vehicle["why"])

        parts = vehicle.get("parts", {})

        for part_key, label in [
            ("requirement", "Requirement"),
            ("distance", "Distance"),
            ("price", "Price"),
            ("availability", "Availability"),
            ("rating", "Rating"),
            ("performance", "Performance"),
        ]:
            bar(
                label,
                parts.get(part_key, 0),
            )

        st.caption(
            f"Owner: {vehicle['owner_name']}  •  "
            f"Capacity: {vehicle['capacity']}  •  "
            f"Reg: {vehicle['registration_number']} "
            "(sample data)"
        )

        if st.button(
            "❤️ Add to favorites",
            key=f"fav_{key}_{vehicle['id']}",
        ):
            db.run(
                "INSERT OR IGNORE INTO favorites VALUES(?, ?)",
                (
                    user_id,
                    vehicle["id"],
                ),
            )

            st.toast("Saved to favorites")


# ---------------------------------------------------------------------------
# FARMER - FIND VEHICLE
# ---------------------------------------------------------------------------

def farmer_find(user):
    st.header("🔎 Find a Vehicle")

    # IMPORTANT:
    # This is a FORM KEY, not a session_state key.
    # It is deliberately different from "req".
    with st.form("vehicle_search_form"):

        # ---------------------------------------------------------------
        # Row 1
        # ---------------------------------------------------------------

        columns = st.columns(3)

        crop = columns[0].selectbox(
            "🌾 Crop",
            CROPS,
            key="find_crop",
        )

        activity = columns[1].selectbox(
            "Farming activity",
            ACTIVITIES,
            key="find_activity",
        )

        acres = columns[2].number_input(
            "Land area (acres)",
            min_value=0.5,
            max_value=500.0,
            value=5.0,
            step=0.5,
            key="find_acres",
        )

        # ---------------------------------------------------------------
        # Row 2
        # ---------------------------------------------------------------

        columns = st.columns(4)

        location_options = list(LOCATIONS)

        user_location = user.get("location")

        if user_location in location_options:
            location_index = location_options.index(user_location)
        else:
            location_index = 0

        location = columns[0].selectbox(
            "📍 Location",
            location_options,
            index=location_index,
            key="find_location",
        )

        required_date = columns[1].date_input(
            "📅 Required date",
            value=dt.date.today() + dt.timedelta(days=3),
            key="find_date",
        )

        hours = columns[2].selectbox(
            "Duration (hours)",
            [2, 4, 6, 8, 10, 16, 24],
            index=3,
            key="find_hours",
        )

        budget = columns[3].number_input(
            "💰 Budget (₹, 0 = no limit)",
            min_value=0,
            max_value=200000,
            value=4000,
            step=500,
            key="find_budget",
        )

        # ---------------------------------------------------------------
        # Row 3
        # ---------------------------------------------------------------

        columns = st.columns(3)

        radius = columns[0].selectbox(
            "Within",
            [5, 10, 25, 50],
            index=3,
            format_func=lambda value: f"{value} km",
            key="find_radius",
        )

        sort_option = columns[1].selectbox(
            "Sort by",
            [
                "AI Recommended",
                "Nearest",
                "Lowest Price",
                "Highest Rating",
                "Best Value",
            ],
            key="find_sort",
        )

        minimum_hp = columns[2].number_input(
            "Minimum HP (optional)",
            min_value=0,
            max_value=120,
            value=0,
            key="find_min_hp",
        )

        find_button = st.form_submit_button(
            "Find vehicles",
            type="primary",
        )

    # -------------------------------------------------------------------
    # PROCESS SEARCH
    # -------------------------------------------------------------------

    if find_button:

        if required_date < dt.date.today():
            st.error(
                "Please select a valid booking date."
            )
            return

        latitude, longitude = LOCATIONS[location]

        request = {
            "lat": latitude,
            "lon": longitude,
            "acres": acres,
            "crop": crop,
            "activity": activity,
            "duration_hours": hours,
            "budget": budget,
            "date": required_date,
        }

        try:
            recommendations = recommend.recommend(
                request,
                radius,
            )
        except Exception as error:
            st.error(
                f"Could not generate vehicle recommendations: {error}"
            )
            return

        results = [
            result
            for result in recommendations
            if result.get("horsepower", 0) >= minimum_hp
        ]

        # ---------------------------------------------------------------
        # SORT RESULTS
        # ---------------------------------------------------------------

        sort_functions = {
            "AI Recommended": lambda result: -result.get(
                "score",
                0,
            ),
            "Nearest": lambda result: result.get(
                "distance_km",
                float("inf"),
            ),
            "Lowest Price": lambda result: result.get(
                "rent_estimate",
                float("inf"),
            ),
            "Highest Rating": lambda result: -result.get(
                "rating",
                0,
            ),
            "Best Value": lambda result: (
                -result.get("score", 0)
                / max(
                    result.get("rent_estimate", 1),
                    1,
                )
            ),
        }

        results.sort(
            key=sort_functions[sort_option]
        )

        # ---------------------------------------------------------------
        # SAVE SEARCH RESULTS TO SESSION STATE
        # ---------------------------------------------------------------

        ss.req = request
        ss.res = results
        ss.loc = location

        # Reset previous price prediction.
        ss.price = None

    # -------------------------------------------------------------------
    # IMPORTANT:
    # Do NOT use ss.req or ss.res until they have been initialized.
    # They were initialized globally above, but get() makes this extra safe.
    # -------------------------------------------------------------------

    request = ss.get("req")
    results = ss.get("res", [])

    if request is None:
        st.info(
            "Enter your requirements above and click "
            "**Find vehicles** to see recommendations."
        )
        return

    if not results:
        st.warning(
            "No vehicles found within the selected distance. "
            "Try a bigger radius, lower minimum HP, or another location."
        )
        return

    # -------------------------------------------------------------------
    # AI PRICE PREDICTION
    # -------------------------------------------------------------------

    top_vehicle_type = results[0]["vehicle_type"]

    try:
        predicted_price = pricing.predict_price(
            top_vehicle_type,
            results[0]["horsepower"],
            ss.loc,
            request["crop"],
            request["activity"],
            request["duration_hours"],
            request["date"].month,
            results[0]["distance_km"],
        )
    except Exception as error:
        st.error(
            f"Price prediction failed: {error}"
        )
        predicted_price = None

    ss.price = predicted_price

    # -------------------------------------------------------------------
    # SMART SUGGESTIONS
    # -------------------------------------------------------------------

    st.subheader("🤖 Smart Suggestions for You")

    try:
        suggestions = suggest.smart_suggestions(
            request,
            results,
            predicted_price,
        )

        for suggestion in suggestions:
            st.write(suggestion)

    except Exception as error:
        st.warning(
            f"Could not generate smart suggestions: {error}"
        )

    # -------------------------------------------------------------------
    # PRICE PREDICTION DISPLAY
    # -------------------------------------------------------------------

    if predicted_price:

        with st.expander(
            f"💰 AI price prediction for "
            f"{top_vehicle_type} "
            f"({request['activity']}, "
            f"{request['duration_hours']}h)",
            expanded=True,
        ):

            columns = st.columns(3)

            columns[0].metric(
                "Low",
                f"₹{predicted_price['low']:,.0f}",
            )

            columns[1].metric(
                "Expected",
                f"₹{predicted_price['expected']:,.0f}",
            )

            columns[2].metric(
                "High",
                f"₹{predicted_price['high']:,.0f}",
            )

            st.write(
                f"Confidence: "
                f"**{predicted_price['confidence']}%**"
                f"  •  "
                f"Season: {predicted_price['season']}"
            )

            factors = predicted_price.get(
                "factors",
                [],
            )

            if factors:
                st.caption(
                    "Main factors: "
                    + ", ".join(
                        f"{name.replace('_', ' ')} "
                        f"({value * 100:.0f}%)"
                        for name, value in factors
                    )
                )

    # -------------------------------------------------------------------
    # MAP
    # -------------------------------------------------------------------

    st.subheader(
        "📍 Map (approximate vehicle locations)"
    )

    points = []

    for result in results:
        latitude = result.get("latitude")
        longitude = result.get("longitude")

        if latitude is not None and longitude is not None:
            points.append(
                {
                    "lat": round(float(latitude), 2),
                    "lon": round(float(longitude), 2),
                }
            )

    points.append(
        {
            "lat": request["lat"],
            "lon": request["lon"],
        }
    )

    if points:
        st.map(
            pd.DataFrame(points),
            zoom=8,
        )

    # -------------------------------------------------------------------
    # VEHICLE RESULTS
    # -------------------------------------------------------------------

    st.subheader(
        f"Found {len(results)} vehicle(s)"
    )

    for index, vehicle in enumerate(results):
        vehicle_card(
            vehicle,
            user["id"],
            index,
        )

    # -------------------------------------------------------------------
    # COMPARE
    # -------------------------------------------------------------------

    st.subheader("⚖️ Compare")

    names = {
        f"{result['brand']} "
        f"{result['model']} "
        f"({result['id']})": result
        for result in results
    }

    selected = st.multiselect(
        "Choose vehicles to compare",
        list(names),
        key="compare_vehicles",
    )

    if selected:
        comparison_data = []

        for name in selected:
            vehicle = names[name]

            comparison_data.append(
                {
                    "Vehicle": name,
                    "Price/day ₹": vehicle.get(
                        "price_per_day",
                        0,
                    ),
                    "Distance km": vehicle.get(
                        "distance_km",
                        0,
                    ),
                    "HP": vehicle.get(
                        "horsepower",
                        0,
                    ),
                    "Rating": vehicle.get(
                        "rating",
                        0,
                    ),
                    "Capacity": vehicle.get(
                        "capacity",
                        "",
                    ),
                    "AI score %": vehicle.get(
                        "score",
                        0,
                    ),
                    "Available": (
                        "Yes"
                        if vehicle.get(
                            "available",
                            False,
                        )
                        else "No"
                    ),
                }
            )

        st.dataframe(
            pd.DataFrame(comparison_data),
            hide_index=True,
            use_container_width=True,
        )

    # -------------------------------------------------------------------
    # BOOK VEHICLE
    # -------------------------------------------------------------------

    st.subheader("📅 Book a vehicle")

    if not names:
        return

    selected_vehicle_name = st.selectbox(
        "Vehicle",
        list(names),
        key="booking_vehicle",
    )

    vehicle = names[selected_vehicle_name]

    hours = request["duration_hours"]

    rent = vehicle.get(
        "rent_estimate",
        0,
    )

    distance = vehicle.get(
        "distance_km",
        0,
    )

    transport = round(
        distance * 12 / 10
    ) * 10

    service_charge = 100

    total = (
        rent
        + transport
        + service_charge
    )

    st.write(
        f"Vehicle rental ₹{rent:,.0f} + "
        f"Transport ₹{transport:,.0f} + "
        f"Service charge ₹{service_charge} = "
        f"**₹{total:,.0f}**  "
        f"(date {request['date']}, "
        f"{hours} h, "
        f"{request['activity']})"
    )

    if st.button(
        "Send booking request",
        type="primary",
        key="send_booking_request",
    ):

        if db.is_booked(
            vehicle["id"],
            request["date"],
        ):
            st.error(
                "This vehicle is already booked "
                "for the selected date."
            )

        elif vehicle.get(
            "availability_status"
        ) != "Available":
            st.error(
                "This vehicle is not available right now."
            )

        else:
            try:
                db.run(
                    """
                    INSERT INTO bookings(
                        farmer_id,
                        vehicle_id,
                        booking_date,
                        duration_value,
                        duration_unit,
                        activity,
                        crop,
                        farm_location,
                        rent,
                        transport_charge,
                        service_charge,
                        total_price
                    )
                    VALUES(
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        user["id"],
                        vehicle["id"],
                        str(request["date"]),
                        hours,
                        "hours",
                        request["activity"],
                        request["crop"],
                        ss.loc,
                        rent,
                        transport,
                        service_charge,
                        total,
                    ),
                )

                if ss.price:
                    db.run(
                        """
                        INSERT INTO ai_logs(
                            kind,
                            predicted,
                            actual
                        )
                        VALUES(
                            'price',
                            ?,
                            ?
                        )
                        """,
                        (
                            ss.price["expected"],
                            total
                            - transport
                            - service_charge,
                        ),
                    )

                db.notify(
                    vehicle["owner_id"],
                    f"New booking request for "
                    f"{vehicle['brand']} "
                    f"{vehicle['model']} "
                    f"on {request['date']}.",
                )

                st.success(
                    "Request sent! Track it under My Bookings."
                )

            except Exception as error:
                st.error(
                    f"Could not create booking: {error}"
                )


# ---------------------------------------------------------------------------
# FARMER - BOOKINGS
# ---------------------------------------------------------------------------

def farmer_bookings(user):
    st.header("📅 My Bookings")

    rows = db.q(
        """
        SELECT
            b.*,
            v.brand,
            v.model,
            v.owner_id
        FROM bookings b
        JOIN vehicles v
            ON v.id = b.vehicle_id
        WHERE b.farmer_id = ?
        ORDER BY b.id DESC
        """,
        (user["id"],),
    )

    if not rows:
        st.info("No bookings yet.")
        return

    for booking in rows:

        with st.container(border=True):

            st.write(
                f"**#{booking['id']} "
                f"{booking['brand']} "
                f"{booking['model']}** — "
                f"{booking['booking_date']} — "
                f"₹{booking['total_price']:,.0f} — "
                f"**{booking['status']}**"
            )

            columns = st.columns(3)

            # -----------------------------------------------------------
            # CONFIRM
            # -----------------------------------------------------------

            if (
                booking["status"] == "Accepted"
                and columns[0].button(
                    "Confirm booking",
                    key=f"confirm_{booking['id']}",
                )
            ):
                db.run(
                    """
                    UPDATE bookings
                    SET status = 'Confirmed'
                    WHERE id = ?
                    """,
                    (booking["id"],),
                )

                db.notify(
                    booking["owner_id"],
                    f"Booking #{booking['id']} "
                    "confirmed by farmer.",
                )

                st.rerun()

            # -----------------------------------------------------------
            # CANCEL
            # -----------------------------------------------------------

            if (
                booking["status"]
                in (
                    "Pending",
                    "Accepted",
                    "Confirmed",
                )
                and columns[1].button(
                    "Cancel",
                    key=f"cancel_{booking['id']}",
                )
            ):
                db.run(
                    """
                    UPDATE bookings
                    SET status = 'Cancelled'
                    WHERE id = ?
                    """,
                    (booking["id"],),
                )

                db.notify(
                    booking["owner_id"],
                    f"Booking #{booking['id']} cancelled.",
                )

                st.rerun()

            # -----------------------------------------------------------
            # ACTIVE VEHICLE LOCATION
            # -----------------------------------------------------------

            if booking["status"] in (
                "Confirmed",
                "In Progress",
            ):
                vehicle = db.q(
                    """
                    SELECT
                        location,
                        latitude,
                        longitude
                    FROM vehicles
                    WHERE id = ?
                    """,
                    (booking["vehicle_id"],),
                    one=True,
                )

                if vehicle:
                    st.caption(
                        f"Vehicle location "
                        f"(shared because of active booking): "
                        f"{vehicle['location']} "
                        f"({vehicle['latitude']:.3f}, "
                        f"{vehicle['longitude']:.3f})"
                    )

            # -----------------------------------------------------------
            # REVIEW
            # -----------------------------------------------------------

            existing_review = db.q(
                """
                SELECT 1
                FROM reviews
                WHERE booking_id = ?
                """,
                (booking["id"],),
                one=True,
            )

            if (
                booking["status"] == "Completed"
                and not existing_review
            ):
                rating = st.slider(
                    "Rating",
                    1,
                    5,
                    5,
                    key=f"rating_{booking['id']}",
                )

                comment = st.text_input(
                    "Comment",
                    key=f"comment_{booking['id']}",
                )

                if st.button(
                    "Submit review",
                    key=f"submit_review_{booking['id']}",
                ):
                    db.run(
                        """
                        INSERT INTO reviews(
                            booking_id,
                            farmer_id,
                            vehicle_id,
                            rating,
                            comment
                        )
                        VALUES(?, ?, ?, ?, ?)
                        """,
                        (
                            booking["id"],
                            user["id"],
                            booking["vehicle_id"],
                            rating,
                            comment,
                        ),
                    )

                    db.notify(
                        booking["owner_id"],
                        f"New {rating}★ review received.",
                    )

                    st.rerun()


# ---------------------------------------------------------------------------
# FARMER - FAVORITES
# ---------------------------------------------------------------------------

def favorites(user):
    st.header("❤️ Favorites")

    rows = db.q(
        """
        SELECT v.*
        FROM favorites f
        JOIN vehicles v
            ON v.id = f.vehicle_id
        WHERE f.user_id = ?
        """,
        (user["id"],),
    )

    if not rows:
        st.info("No favorites yet.")
        return

    dataframe = pd.DataFrame(rows)

    columns = [
        "brand",
        "model",
        "vehicle_type",
        "horsepower",
        "price_per_day",
        "location",
        "availability_status",
    ]

    available_columns = [
        column
        for column in columns
        if column in dataframe.columns
    ]

    st.dataframe(
        dataframe[available_columns],
        hide_index=True,
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# FARMER - NOTIFICATIONS
# ---------------------------------------------------------------------------

def notifications(user):
    st.header("🔔 Notifications")

    rows = db.q(
        """
        SELECT *
        FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 30
        """,
        (user["id"],),
    )

    if not rows:
        st.info("No notifications.")
    else:
        for notification in rows:
            created_at = notification.get(
                "created_at",
                "",
            )

            st.write(
                f"• {created_at[:16]} — "
                f"{notification['message']}"
            )

    db.run(
        """
        UPDATE notifications
        SET read_status = 1
        WHERE user_id = ?
        """,
        (user["id"],),
    )

    with st.expander("Report a problem"):

        message = st.text_area(
            "Describe the problem",
            key="complaint_message",
        )

        if (
            st.button(
                "Send complaint",
                key="send_complaint",
            )
            and message.strip()
        ):
            db.run(
                """
                INSERT INTO complaints(
                    user_id,
                    message
                )
                VALUES(?, ?)
                """,
                (
                    user["id"],
                    message.strip(),
                ),
            )

            st.success(
                "Your complaint has been sent to admin."
            )


# ---------------------------------------------------------------------------
# FARMER - AI CHAT
# ---------------------------------------------------------------------------

def chat(user):
    st.header("🤖 AgriAssist AI")

    st.caption(
        "Answers come only from live platform data "
        "(vehicles, prices, availability). "
        "Optional: Ollama can reword answers."
    )

    use_ollama = st.toggle(
        "Use local Ollama to reword (optional)",
        False,
        key="use_ollama",
    )

    # Ensure chat always exists.
    if "chat" not in ss:
        ss.chat = []

    for role, message in ss.chat:
        with st.chat_message(role):
            st.text(message)

    user_message = st.chat_input(
        "e.g. I have ₹5000 budget. What can I book?"
    )

    if user_message:

        ss.chat.append(
            ("user", user_message)
        )

        try:
            answer = assistant.answer(
                user_message,
                user,
                use_ollama,
            )
        except Exception as error:
            answer = (
                "Sorry, I could not process that request. "
                f"Error: {error}"
            )

        ss.chat.append(
            ("assistant", answer)
        )

        st.rerun()


# ---------------------------------------------------------------------------
# OWNER - VEHICLES
# ---------------------------------------------------------------------------

def owner_vehicles(user):
    st.header("🚜 My Vehicles")

    if user["verification_status"] != "verified":
        st.warning(
            "Your account is waiting for admin verification. "
            "Vehicles are hidden from farmers until then."
        )

    vehicles = db.q(
        """
        SELECT *
        FROM vehicles
        WHERE owner_id = ?
        """,
        (user["id"],),
    )

    for vehicle in vehicles:

        with st.container(border=True):

            st.write(
                f"**{vehicle['brand']} "
                f"{vehicle['model']}** "
                f"({vehicle['vehicle_type']}, "
                f"{vehicle['horsepower']} HP) — "
                f"₹{vehicle['price_per_hour']:.0f}/h, "
                f"₹{vehicle['price_per_day']:.0f}/day"
            )

            columns = st.columns(
                [2, 2, 1]
            )

            status_options = [
                "Available",
                "Busy",
                "Maintenance",
                "Offline",
            ]

            current_status = vehicle[
                "availability_status"
            ]

            if current_status not in status_options:
                current_status = "Offline"

            new_status = columns[0].selectbox(
                "Status",
                status_options,
                index=status_options.index(
                    current_status
                ),
                key=f"vehicle_status_{vehicle['id']}",
            )

            location_options = list(LOCATIONS)

            current_location = vehicle.get(
                "location"
            )

            if current_location in location_options:
                location_index = location_options.index(
                    current_location
                )
            else:
                location_index = 0

            new_location = columns[1].selectbox(
                "Current location",
                location_options,
                index=location_index,
                key=f"vehicle_location_{vehicle['id']}",
            )

            if columns[2].button(
                "Update",
                key=f"update_vehicle_{vehicle['id']}",
            ):
                latitude, longitude = LOCATIONS[
                    new_location
                ]

                db.run(
                    """
                    UPDATE vehicles
                    SET
                        availability_status = ?,
                        location = ?,
                        latitude = ?,
                        longitude = ?
                    WHERE id = ?
                    """,
                    (
                        new_status,
                        new_location,
                        latitude,
                        longitude,
                        vehicle["id"],
                    ),
                )

                st.success(
                    "Vehicle updated."
                )

                st.rerun()

    # -------------------------------------------------------------------
    # ADD VEHICLE
    # -------------------------------------------------------------------

    with st.expander("➕ Add vehicle"):

        database_types = [
            row["name"]
            for row in db.q(
                "SELECT name FROM vehicle_types"
            )
        ]

        vehicle_types = (
            database_types
            or VEHICLE_TYPES
        )

        columns = st.columns(3)

        vehicle_type = columns[0].selectbox(
            "Type",
            vehicle_types,
            key="new_vehicle_type",
        )

        brand = columns[1].text_input(
            "Brand",
            key="new_vehicle_brand",
        )

        model = columns[2].text_input(
            "Model",
            key="new_vehicle_model",
        )

        columns = st.columns(4)

        registration = columns[0].text_input(
            "Registration no.",
            key="new_vehicle_registration",
        )

        horsepower = columns[1].number_input(
            "Horsepower",
            min_value=0,
            max_value=500,
            value=45,
            key="new_vehicle_hp",
        )

        capacity = columns[2].text_input(
            "Capacity",
            key="new_vehicle_capacity",
        )

        location = columns[3].selectbox(
            "Location",
            list(LOCATIONS),
            key="new_vehicle_location",
        )

        columns = st.columns(2)

        price_hour = columns[0].number_input(
            "Price per hour ₹",
            min_value=0,
            max_value=20000,
            value=400,
            key="new_vehicle_price_hour",
        )

        price_day = columns[1].number_input(
            "Price per day ₹",
            min_value=0,
            max_value=200000,
            value=3000,
            key="new_vehicle_price_day",
        )

        image_file = st.file_uploader(
            "Vehicle image (optional)",
            type=["png", "jpg", "jpeg"],
            key="new_vehicle_image",
        )

        if st.button(
            "Save vehicle",
            type="primary",
            key="save_vehicle",
        ):

            if (
                not brand.strip()
                or not model.strip()
            ):
                st.error(
                    "Brand and model are required."
                )

            else:
                image_path = None

                if image_file:
                    os.makedirs(
                        "uploads",
                        exist_ok=True,
                    )

                    safe_filename = (
                        f"{user['id']}_"
                        f"{image_file.name}"
                    )

                    image_path = os.path.join(
                        "uploads",
                        safe_filename,
                    )

                    with open(
                        image_path,
                        "wb",
                    ) as file:
                        file.write(
                            image_file.getbuffer()
                        )

                latitude, longitude = LOCATIONS[
                    location
                ]

                try:
                    db.run(
                        """
                        INSERT INTO vehicles(
                            owner_id,
                            vehicle_type,
                            brand,
                            model,
                            registration_number,
                            horsepower,
                            capacity,
                            price_per_hour,
                            price_per_day,
                            location,
                            latitude,
                            longitude,
                            image
                        )
                        VALUES(
                            ?, ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?, ?, ?
                        )
                        """,
                        (
                            user["id"],
                            vehicle_type,
                            brand.strip(),
                            model.strip(),
                            registration,
                            horsepower,
                            capacity,
                            price_hour,
                            price_day,
                            location,
                            latitude,
                            longitude,
                            image_path,
                        ),
                    )

                    st.success(
                        "Vehicle added successfully."
                    )

                    st.rerun()

                except Exception as error:
                    st.error(
                        f"Could not save vehicle: {error}"
                    )


# ---------------------------------------------------------------------------
# OWNER - BOOKING REQUESTS
# ---------------------------------------------------------------------------

def owner_requests(user):
    st.header("📥 Booking Requests")

    rows = db.q(
        """
        SELECT
            b.*,
            v.brand,
            v.model,
            f.name AS fname
        FROM bookings b
        JOIN vehicles v
            ON v.id = b.vehicle_id
        JOIN users f
            ON f.id = b.farmer_id
        WHERE v.owner_id = ?
        ORDER BY b.id DESC
        """,
        (user["id"],),
    )

    next_actions = {
        "Pending": [
            ("Accept", "Accepted"),
            ("Reject", "Rejected"),
        ],
        "Confirmed": [
            ("Start work", "In Progress"),
        ],
        "In Progress": [
            ("Mark completed", "Completed"),
        ],
    }

    if not rows:
        st.info(
            "No booking requests."
        )
        return

    for booking in rows:

        with st.container(border=True):

            st.write(
                f"**#{booking['id']}** "
                f"{booking['brand']} "
                f"{booking['model']} — "
                f"{booking['fname']} — "
                f"{booking['booking_date']} — "
                f"{booking['activity']} "
                f"({booking['crop']}) — "
                f"₹{booking['total_price']:,.0f} — "
                f"**{booking['status']}**"
            )

            actions = next_actions.get(
                booking["status"],
                [],
            )

            for index, (
                label,
                new_status,
            ) in enumerate(actions):

                if st.button(
                    label,
                    key=(
                        f"owner_action_"
                        f"{new_status}_"
                        f"{booking['id']}_"
                        f"{index}"
                    ),
                ):

                    if (
                        new_status == "Accepted"
                        and db.is_booked(
                            booking["vehicle_id"],
                            booking["booking_date"],
                        )
                    ):
                        st.error(
                            "Date already booked."
                        )
                        continue

                    db.run(
                        """
                        UPDATE bookings
                        SET status = ?
                        WHERE id = ?
                        """,
                        (
                            new_status,
                            booking["id"],
                        ),
                    )

                    db.notify(
                        booking["farmer_id"],
                        f"Booking #{booking['id']} "
                        f"is now {new_status}.",
                    )

                    st.rerun()


# ---------------------------------------------------------------------------
# OWNER - EARNINGS
# ---------------------------------------------------------------------------

def owner_earnings(user):
    st.header("💵 Earnings")

    result = db.q(
        """
        SELECT
            COALESCE(
                SUM(
                    b.rent
                    + b.transport_charge
                ),
                0
            ) AS e,
            COUNT(*) AS n
        FROM bookings b
        JOIN vehicles v
            ON v.id = b.vehicle_id
        WHERE
            v.owner_id = ?
            AND b.status = 'Completed'
        """,
        (user["id"],),
        one=True,
    )

    columns = st.columns(2)

    columns[0].metric(
        "Total earnings",
        f"₹{result['e']:,.0f}",
    )

    columns[1].metric(
        "Completed jobs",
        result["n"],
    )

    st.header("⭐ Reviews")

    reviews = db.q(
        """
        SELECT
            r.rating,
            r.comment,
            v.brand,
            v.model
        FROM reviews r
        JOIN vehicles v
            ON v.id = r.vehicle_id
        WHERE v.owner_id = ?
        """,
        (user["id"],),
    )

    if not reviews:
        st.info(
            "No reviews yet."
        )
        return

    for review in reviews:
        st.write(
            f"{'⭐' * review['rating']} "
            f"{review['brand']} "
            f"{review['model']} — "
            f"{review['comment']}"
        )


# ---------------------------------------------------------------------------
# ADMIN - DASHBOARD
# ---------------------------------------------------------------------------

def admin_dash(user):
    st.header("📊 Admin Dashboard")

    def count(sql):
        result = db.q(
            sql,
            one=True,
        )

        return result["n"] if result else 0

    columns = st.columns(4)

    columns[0].metric(
        "Farmers",
        count(
            """
            SELECT COUNT(*) n
            FROM users
            WHERE role = 'farmer'
            """
        ),
    )

    columns[1].metric(
        "Owners",
        count(
            """
            SELECT COUNT(*) n
            FROM users
            WHERE role = 'owner'
            """
        ),
    )

    columns[2].metric(
        "Vehicles",
        count(
            """
            SELECT COUNT(*) n
            FROM vehicles
            """
        ),
    )

    columns[3].metric(
        "Bookings",
        count(
            """
            SELECT COUNT(*) n
            FROM bookings
            """
        ),
    )

    columns = st.columns(4)

    platform_revenue = count(
        """
        SELECT
            COALESCE(
                SUM(service_charge),
                0
            ) n
        FROM bookings
        WHERE status = 'Completed'
        """
    )

    columns[0].metric(
        "Platform revenue",
        f"₹{platform_revenue:,.0f}",
    )

    columns[1].metric(
        "Active vehicles",
        count(
            """
            SELECT COUNT(*) n
            FROM vehicles
            WHERE availability_status = 'Available'
            """
        ),
    )

    columns[2].metric(
        "Pending verification",
        count(
            """
            SELECT COUNT(*) n
            FROM users
            WHERE
                role = 'owner'
                AND verification_status = 'pending'
            """
        ),
    )

    columns[3].metric(
        "Open complaints",
        count(
            """
            SELECT COUNT(*) n
            FROM complaints
            WHERE status = 'Open'
            """
        ),
    )

    tab1, tab2 = st.tabs(
        [
            "Popular vehicle types",
            "Bookings by status",
        ]
    )

    # Vehicle types
    vehicle_data = pd.DataFrame(
        db.q(
            """
            SELECT
                v.vehicle_type AS t,
                COUNT(*) AS n
            FROM bookings b
            JOIN vehicles v
                ON v.id = b.vehicle_id
            GROUP BY v.vehicle_type
            """
        )
    )

    if not vehicle_data.empty:
        tab1.bar_chart(
            vehicle_data.set_index("t")
        )

    # Booking statuses
    booking_data = pd.DataFrame(
        db.q(
            """
            SELECT
                status AS s,
                COUNT(*) AS n
            FROM bookings
            GROUP BY status
            """
        )
    )

    if not booking_data.empty:
        tab2.bar_chart(
            booking_data.set_index("s")
        )

    # Monthly bookings
    monthly_data = pd.DataFrame(
        db.q(
            """
            SELECT
                substr(
                    booking_date,
                    1,
                    7
                ) AS m,
                COUNT(*) AS n
            FROM bookings
            GROUP BY m
            """
        )
    )

    if not monthly_data.empty:
        st.subheader(
            "Monthly bookings"
        )

        st.line_chart(
            monthly_data.set_index("m")
        )


# ---------------------------------------------------------------------------
# ADMIN - MANAGE
# ---------------------------------------------------------------------------

def admin_manage(user):
    st.header("🛠 Manage Platform")

    # -------------------------------------------------------------------
    # VERIFY OWNERS
    # -------------------------------------------------------------------

    st.subheader(
        "Verify vehicle owners"
    )

    owners = db.q(
        """
        SELECT
            id,
            name,
            email,
            location,
            verification_status
        FROM users
        WHERE role = 'owner'
        """
    )

    if not owners:
        st.info(
            "No vehicle owners found."
        )

    for owner in owners:

        columns = st.columns(
            [3, 2, 2]
        )

        columns[0].write(
            f"{owner['name']} "
            f"({owner['email']})"
        )

        columns[1].write(
            owner["verification_status"]
        )

        if (
            owner["verification_status"]
            != "verified"
            and columns[2].button(
                "Verify",
                key=f"verify_owner_{owner['id']}",
            )
        ):
            db.run(
                """
                UPDATE users
                SET verification_status = 'verified'
                WHERE id = ?
                """,
                (owner["id"],),
            )

            db.notify(
                owner["id"],
                "Your account is verified.",
            )

            st.rerun()

    # -------------------------------------------------------------------
    # COMPLAINTS
    # -------------------------------------------------------------------

    st.subheader("Complaints")

    complaints = db.q(
        """
        SELECT *
        FROM complaints
        ORDER BY id DESC
        """
    )

    if not complaints:
        st.info(
            "No complaints."
        )

    for complaint in complaints:

        st.write(
            f"#{complaint['id']} "
            f"[{complaint['status']}] "
            f"{complaint['message']}"
        )

        if (
            complaint["status"] == "Open"
            and st.button(
                "Resolve",
                key=f"resolve_complaint_{complaint['id']}",
            )
        ):
            db.run(
                """
                UPDATE complaints
                SET status = 'Resolved'
                WHERE id = ?
                """,
                (complaint["id"],),
            )

            st.rerun()

    # -------------------------------------------------------------------
    # ADD VEHICLE TYPE
    # -------------------------------------------------------------------

    st.subheader(
        "Add vehicle type"
    )

    new_type = st.text_input(
        "New vehicle type",
        key="admin_new_vehicle_type",
    )

    if (
        st.button(
            "Add type",
            key="admin_add_vehicle_type",
        )
        and new_type.strip()
    ):
        db.run(
            """
            INSERT OR IGNORE INTO vehicle_types(name)
            VALUES(?)
            """,
            (new_type.strip(),),
        )

        st.success(
            "Vehicle type added."
        )

    # -------------------------------------------------------------------
    # DATA TABLES
    # -------------------------------------------------------------------

    tables = [
        (
            "Users",
            """
            SELECT
                id,
                name,
                email,
                role,
                location,
                verification_status
            FROM users
            """,
        ),
        (
            "Vehicles",
            """
            SELECT
                id,
                owner_id,
                vehicle_type,
                brand,
                model,
                price_per_day,
                availability_status,
                is_demo
            FROM vehicles
            """,
        ),
        (
            "Bookings",
            """
            SELECT
                id,
                farmer_id,
                vehicle_id,
                booking_date,
                total_price,
                status
            FROM bookings
            """,
        ),
    ]

    for name, sql in tables:

        with st.expander(name):

            data = pd.DataFrame(
                db.q(sql)
            )

            st.dataframe(
                data,
                hide_index=True,
                use_container_width=True,
            )


# ---------------------------------------------------------------------------
# ADMIN - AI ANALYTICS
# ---------------------------------------------------------------------------

def admin_ai(user):
    st.header(
        "🧠 AI Analytics – Price Prediction Model"
    )

    try:
        metrics = pricing.metrics()
    except Exception as error:
        st.error(
            f"Could not load model metrics: {error}"
        )
        return

    st.success(
        f"Best model: **{metrics['best_model']}** "
        f"(train {metrics['n_train']} / "
        f"test {metrics['n_test']} rows)"
    )

    results = pd.DataFrame(
        metrics["results"]
    ).T.rename(
        columns={
            "MAE": "MAE (₹)",
            "RMSE": "RMSE (₹)",
            "R2": "R² score",
        }
    )

    st.dataframe(
        results,
        use_container_width=True,
    )

    st.caption(
        metrics["note"]
    )

    st.subheader(
        "Feature importance"
    )

    st.bar_chart(
        pd.Series(
            metrics["importance"]
        )
    )

    # -------------------------------------------------------------------
    # ACTUAL VS PREDICTED
    # -------------------------------------------------------------------

    actual_predicted_path = os.path.join(
        pricing.ML,
        "actual_vs_predicted.csv",
    )

    if os.path.exists(
        actual_predicted_path
    ):
        actual_predicted = pd.read_csv(
            actual_predicted_path
        )

        st.subheader(
            "Actual vs predicted price"
        )

        st.scatter_chart(
            actual_predicted,
            x="actual",
            y="predicted",
        )

    # -------------------------------------------------------------------
    # RENTAL PRICE DATA
    # -------------------------------------------------------------------

    rental_data_path = os.path.join(
        os.path.dirname(pricing.ML),
        "data",
        "rental_prices.csv",
    )

    if not os.path.exists(
        rental_data_path
    ):
        st.warning(
            "Rental price training data was not found."
        )
        return

    data = pd.read_csv(
        rental_data_path
    )

    columns = st.columns(2)

    columns[0].subheader(
        "Average price by vehicle type"
    )

    columns[0].bar_chart(
        data.groupby(
            "vehicle_type"
        )["price"].mean()
    )

    columns[1].subheader(
        "Average price by location"
    )

    columns[1].bar_chart(
        data.groupby(
            "location"
        )["price"].mean()
    )

    st.subheader(
        "Demand by month"
    )

    st.line_chart(
        data.groupby(
            "month"
        )["demand"].mean()
    )

    st.subheader(
        "Recommendation weights "
        "(edit core/recommend.py → WEIGHTS)"
    )

    st.json(
        recommend.WEIGHTS
    )


# ---------------------------------------------------------------------------
# ROUTER
# ---------------------------------------------------------------------------

def main():

    # Always initialize session state before reading it.
    ss.setdefault("user", None)
    ss.setdefault("req", None)
    ss.setdefault("res", [])
    ss.setdefault("loc", None)
    ss.setdefault("price", None)
    ss.setdefault("chat", [])

    user = ss.get("user")

    # ---------------------------------------------------------------
    # NOT LOGGED IN
    # ---------------------------------------------------------------

    if not user:
        landing()
        return

    # ---------------------------------------------------------------
    # NOTIFICATION COUNT
    # ---------------------------------------------------------------

    unread_result = db.q(
        """
        SELECT COUNT(*) n
        FROM notifications
        WHERE
            user_id = ?
            AND read_status = 0
        """,
        (user["id"],),
        one=True,
    )

    unread = (
        unread_result["n"]
        if unread_result
        else 0
    )

    # ---------------------------------------------------------------
    # SIDEBAR
    # ---------------------------------------------------------------

    st.sidebar.title(
        "🚜 AgriConnect AI"
    )

    st.sidebar.write(
        f"👤 {user['name']} "
        f"({user['role']})"
    )

    # ---------------------------------------------------------------
    # PAGES
    # ---------------------------------------------------------------

    page_sets = {
        "farmer": {
            "🔎 Find Vehicles": farmer_find,
            "📅 My Bookings": farmer_bookings,
            "❤️ Favorites": favorites,
            f"🔔 Notifications ({unread})": notifications,
            "🤖 AgriAssist": chat,
        },

        "owner": {
            "🚜 My Vehicles": owner_vehicles,
            "📥 Booking Requests": owner_requests,
            "💵 Earnings & Reviews": owner_earnings,
            f"🔔 Notifications ({unread})": notifications,
        },

        "admin": {
            "📊 Dashboard": admin_dash,
            "🛠 Manage": admin_manage,
            "🧠 AI Analytics": admin_ai,
        },
    }

    pages = page_sets.get(
        user.get("role")
    )

    # Handle an invalid role gracefully.
    if not pages:
        st.error(
            "Invalid user role. Please log in again."
        )

        if st.button(
            "Logout",
            key="invalid_role_logout",
        ):
            logout()
            st.rerun()

        return

    # ---------------------------------------------------------------
    # PAGE NAVIGATION
    # ---------------------------------------------------------------

    page = st.sidebar.radio(
        "Menu",
        list(pages),
        key="main_navigation",
    )

    pages[page](user)

    # ---------------------------------------------------------------
    # LOGOUT
    # ---------------------------------------------------------------

    st.sidebar.button(
        "Logout",
        on_click=logout,
        key="logout_button",
    )

    st.sidebar.caption(
        "Demo/sample data is labelled. "
        "AI price model trained on simulated rental data."
    )


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
