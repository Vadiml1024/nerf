import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from os import getenv
import os
import subprocess
import time


# Initialize connection.
# Uses st.cache_resource to only run once.
@st.cache_resource
def init_connection():
    try:
        load_dotenv()
        db_host = getenv("DB_HOST")
        db_port = getenv("DB_PORT", 3306)
        db_name = getenv("DB_NAME")
        db_user = getenv("DB_USER")
        db_pass = getenv("DB_PASSWORD")
        return mysql.connector.connect(
            host=db_host,  # Change this to your Docker container's IP if needed
            port=int(db_port),  # Specify the port if it's not the default
            database=db_name,
            user=db_user,
            password=db_pass,
            #            auth_plugin='mysql_native_password'
        )
    except Error as e:
        st.error(f"Error connecting to MySQL Database: {e}")
        return None


# Perform query.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
# st.cache_data(ttl=600)
def run_query(query, params=None):
    conn = init_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
            return cur.fetchall()
    except Error as e:
        st.error(f"Error executing query: {e}")
        return None


def execute_and_commit(query, params=None):
    conn = init_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
        conn.commit()
        return True
    except Error as e:
        st.error(f"Error executing query: {e}")
        conn.rollback()
        return False


def get_all_rows(table_name):
    query = f"SELECT * FROM {table_name}"
    return run_query(query)


def search_row(table_name, id_column, id_value):
    query = f"SELECT * FROM {table_name} WHERE {id_column} = %s"
    result = run_query(query, (id_value,))
    return result[0] if result else None


def update_row(table_name, id_column, id_value, column_values):
    set_clause = ", ".join([f"{col} = %s" for col in column_values.keys()])
    query = f"UPDATE {table_name} SET {set_clause} WHERE {id_column} = %s"
    values = list(column_values.values()) + [id_value]
    return execute_and_commit(query, values)


def delete_row(table_name, id_column, id_value):
    print("Enter delete-row\n")
    conn = init_connection()
    if not conn:
        return False

    try:
        with conn.cursor() as cur:
            print("In delete-row\n")
            query = f"DELETE FROM {table_name} WHERE {id_column} = %s"
            cur.execute(query, (id_value,))
            conn.commit()
            print("After commit\n")
        return cur.rowcount > 0  # Check if any row was actually deleted
    except Error as e:
        st.error(f"Error deleting row: {e}")
        conn.rollback()
        return False
    finally:
        if conn.is_connected():
            conn.close()


def insert_row(table_name, column_values):
    columns = ", ".join(column_values.keys())
    placeholders = ", ".join(["%s"] * len(column_values))
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
    return execute_and_commit(query, list(column_values.values()))


def backup_database():
    try:
        load_dotenv()
        db_name = getenv("DB_NAME")
        db_user = getenv("DB_USER")
        db_pass = getenv("DB_PASSWORD")
        docker_name = getenv("DB_DOCKER_NAME", "nerf-db-1")  # Add default container name

        # Create backups directory if it doesn't exist
        backup_dir = "database_backups"
        os.makedirs(backup_dir, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"backup_{timestamp}.sql")

        # Construct docker exec mysqldump command
        command = [
            "docker",
            "exec",
            docker_name,  # Use container name from env
            "mysqldump",
            f"--user={db_user}",
            f"--password={db_pass}",
            "--routines",
            "--triggers",
            "--events",
            db_name,
        ]

        # Execute backup
        with open(backup_file, "w") as f:
            subprocess.run(command, stdout=f, check=True)

        return True, backup_file
    except Exception as e:
        return False, str(e)


def restore_database(backup_file):
    try:
        # Get a fresh connection
        conn = init_connection()
        if conn and conn.is_connected():
            conn.close()  # Explicitly close the connection

        # Clear all Streamlit cache
        st.cache_resource.clear()
        st.cache_data.clear()

        load_dotenv()
        db_name = getenv("DB_NAME")
        db_user = getenv("DB_USER")
        db_pass = getenv("DB_PASSWORD")
        docker_name = getenv("DB_DOCKER_NAME", "nerf-db-1")

        # Construct shell command with input redirection
        shell_command = f'docker exec -i {docker_name} mysql --user={db_user} --password={db_pass} --force {db_name} < "{backup_file}"'

        # Execute restore using shell=True to handle redirection
        process = subprocess.run(shell_command, shell=True, capture_output=True, text=True)

        if process.returncode != 0:
            return False, process.stderr

        # Clear cache after restore to force new connection
        st.cache_resource.clear()
        st.cache_data.clear()

        return True, "Database restored successfully"
    except Exception as e:
        # Ensure we clear cache even if restore fails
        st.cache_resource.clear()
        st.cache_data.clear()
        return False, str(e)


def get_gun_status():
    query = "SELECT config_value FROM system_config WHERE config_key = 'gun_active'"
    result = run_query(query)
    if result and result[0]:
        return int(result[0][0]) != 0
    return False


def set_gun_status(active):
    value = "1" if active else "0"
    query = "UPDATE system_config SET config_value = %s WHERE config_key = 'gun_active'"
    return execute_and_commit(query, (value,))


def ensure_bonus_credits_column_exists():
    """
    Check if the 'bonus_credits' column exists in the 'subscribers' table.
    If not, add it with a default value of 0.
    """
    conn = init_connection()
    if not conn:
        st.error("Could not verify 'bonus_credits' column - database connection failed")
        return

    try:
        with conn.cursor() as cur:
            # Check if the column exists
            db_name = getenv("DB_NAME")
            query = """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = 'subscribers'
              AND column_name = 'bonus_credits'
            """
            cur.execute(query, (db_name,))
            column_exists = cur.fetchone()[0]

            if not column_exists:
                st.info("Adding missing 'bonus_credits' column to 'subscribers' table.")
                alter_query = """
                ALTER TABLE subscribers
                ADD COLUMN bonus_credits INT NOT NULL DEFAULT 0 AFTER current_credits
                """
                cur.execute(alter_query)
                conn.commit()
                st.success("'bonus_credits' column added successfully.")
    except Error as e:
        st.error(f"Error checking or adding 'bonus_credits' column: {e}")
        conn.rollback()


@st.fragment(run_every=5)
def show_gun_status():
    current_status = get_gun_status()

    if current_status:
        st.markdown(
            """
            <style>
            div.stButton > button {
                background-color: #28a745;
                color: white;
            }
            div.stButton > button:hover {
                background-color: #218838;
                color: white;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        button_text = "Gun Active"
    else:
        st.markdown(
            """
            <style>
            div.stButton > button {
                background-color: #dc3545;
                color: white;
            }
            div.stButton > button:hover {
                background-color: #c82333;
                color: white;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        button_text = "Gun Inactive"

    if st.button(button_text, key="gun_toggle"):
        new_status = not current_status
        if set_gun_status(new_status):
            st.success(f"Gun {'activated' if new_status else 'deactivated'} successfully!")
            st.rerun()
        else:
            st.error("Failed to update gun status!")


def ensure_system_config_defaults():
    """
    Ensure all required system_config rows exist in the database.
    If any required row is missing, it will be created with a default value.
    """
    required_configs = {
        "min_horizontal_angle": "0",
        "max_horizontal_angle": "180",
        "min_vertical_angle": "0", 
        "max_vertical_angle": "90",
        "home_x": "90",
        "home_y": "45",
        "gun_active": "1",
        "idle_timeout": "300",
        "horizontal_offset": "-45",
        "vertical_offset": "-60",
    }
    
    # Fetch existing config_keys
    query = "SELECT config_key FROM system_config"
    existing_keys = run_query(query)
    
    if existing_keys is None:  # Handle DB connection errors
        st.error("Could not verify system configuration defaults - database connection failed")
        return
    
    existing_keys = [row[0] for row in existing_keys]
    
    # Insert any missing keys with default values
    for key, default_value in required_configs.items():
        if key not in existing_keys:
            st.info(f"Adding missing system_config key: {key} with default value: {default_value}")
            insert_query = "INSERT INTO system_config (config_key, config_value) VALUES (%s, %s)"
            if not execute_and_commit(insert_query, (key, default_value)):
                st.error(f"Failed to add required system_config key: {key}")


def main():
    st.title("NerfBot Database Management")

    # Ensure all required system_config rows exist
    ensure_system_config_defaults()
    ensure_bonus_credits_column_exists()
    
    execute_and_commit("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
    # Add Gun Control button at the top of the sidebar
    st.sidebar.markdown("### Gun Control")

    # Create a container in the sidebar for the gun status
    with st.sidebar:
        show_gun_status()

    st.sidebar.markdown("---")  # Add separator after gun control

    # Sidebar for navigation
    table = st.sidebar.selectbox(
        "Choose a table", ["subscribers", "subscription_levels", "system_config"]
    )
    action = st.sidebar.selectbox(
        "Choose an action", ["View", "Search", "Update", "Delete", "Insert", "Bonus Credits"]
    )

    if table == "subscribers":
        id_column = "user_id"
        columns = [
            "user_id",
            "id",
            "subscription_level",
            "current_credits",
            "bonus_credits",
            "subscription_anniversary",
            "last_reset_date",
        ]
        display_columns = [
            "User ID",
            "ID",
            "Subscription Level",
            "Current Credits",
            "Bonus Credits",
            "Subscription Anniversary",
            "Last Reset Date",
        ]
        date_columns = ["subscription_anniversary", "last_reset_date"]
    elif table == "subscription_levels":
        id_column = "subscription_level"
        columns = ["subscription_level", "max_credits_per_day", "credits_per_shot"]
        display_columns = ["Subscription Level", "Max Credits Per Day", "Credits Per Shot"]
        date_columns = []
    else:  # system_config
        id_column = "config_key"
        columns = ["config_key", "config_value"]
        display_columns = ["Config Key", "Config Value"]
        date_columns = []

    if action == "View":
        st.header(f"All {table.capitalize()}")
        rows = get_all_rows(table)
        if rows:
            df = pd.DataFrame(rows, columns=columns)
            df.columns = display_columns  # Set display column names
            st.dataframe(df)
        else:
            st.info(f"No {table} found.")

    elif action == "Search":
        st.header(f"Search {table.capitalize()}")
        search_value = st.text_input(f"Enter {id_column}")
        if st.button("Search"):
            row = search_row(table, id_column, search_value)
            if row:
                st.success(f"{table.capitalize()} found!")
                df = pd.DataFrame([row], columns=columns)
                df.columns = display_columns  # Set display column names
                st.write(df)
            else:
                st.warning(f"{table.capitalize()} not found.")

    elif action == "Update":
        st.header(f"Update {table.capitalize()}")

        if "update_stage" not in st.session_state:
            st.session_state.update_stage = "search"

        if "search_value" not in st.session_state:
            st.session_state.search_value = ""

        search_value = st.text_input(
            f"Enter {id_column} to update", value=st.session_state.search_value
        )

        if st.button("Search for Update") or st.session_state.update_stage == "edit":
            row = search_row(table, id_column, search_value)
            if row:
                st.session_state.update_row = row
                st.session_state.update_stage = "edit"
                st.session_state.search_value = search_value
            else:
                st.warning(f"{table.capitalize()} not found.")
                st.session_state.update_stage = "search"

        if st.session_state.update_stage == "edit":
            st.success(f"{table.capitalize()} found! Update the fields below:")
            row = st.session_state.update_row
            new_values = {}
            for i, col in enumerate(columns):
                if col != id_column and col != "id":
                    if col in date_columns:
                        new_values[col] = st.date_input(f"New {display_columns[i]}", value=row[i])
                    elif "level" in col or "credits" in col:
                        new_values[col] = st.number_input(
                            f"New {display_columns[i]}", value=row[i], min_value=-1000, max_value=1000
                        )
                    else:
                        new_values[col] = st.text_input(f"New {display_columns[i]}", value=row[i])

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Confirm Update"):
                    if update_row(table, id_column, row[columns.index(id_column)], new_values):
                        st.success(f"{table.capitalize()} updated successfully!")
                        st.session_state.update_stage = "search"
                        st.session_state.search_value = ""
                    else:
                        st.error(f"Failed to update {table}.")

            with col2:
                if st.button("Cancel Update"):
                    st.session_state.update_stage = "search"
                    st.session_state.search_value = ""

    elif action == "Insert":
        st.header(f"Insert New {table.capitalize()}")
        new_values = {}
        for i, col in enumerate(columns):
            if col != "id":
                if col == "subscription_anniversary":
                    default_anniversary = (datetime.now() + timedelta(days=30)).date()
                    new_values[col] = st.date_input(
                        f"{display_columns[i]} (default: 30 days from today)",
                        value=default_anniversary,
                    )
                elif col == "last_reset_date":
                    default_reset = datetime.now().date()
                    new_values[col] = st.date_input(
                        f"{display_columns[i]} (default: today)", value=default_reset
                    )
                elif col in date_columns:
                    new_values[col] = st.date_input(f"{display_columns[i]}")
                elif "level" in col or "credits" in col:
                    new_values[col] = st.number_input(f"{display_columns[i]}", min_value=-1000, max_value=1000)
                else:
                    new_values[col] = st.text_input(f"{display_columns[i]}")
        if st.button("Insert"):
            if insert_row(table, new_values):
                st.success(f"New {table.capitalize()} inserted successfully!")
            else:
                st.error(f"Failed to insert new {table}.")

    elif action == "Bonus Credits":
        st.header("Add Bonus Credits")
        user_id = st.text_input("Enter User ID")
        amount = st.number_input("Amount", min_value=0)
        if st.button("Add Credits"):
            row = search_row("subscribers", "user_id", user_id)
            if row:
                current_bonus = row[columns.index("bonus_credits")]
                new_bonus = current_bonus + amount
                if update_row("subscribers", "user_id", user_id, {"bonus_credits": new_bonus}):
                    st.success(f"Added {amount} bonus credits to {user_id}. They now have {new_bonus} bonus credits.")
                else:
                    st.error("Failed to update bonus credits.")
            else:
                st.warning("User not found.")

    # Add backup and restore buttons to sidebar
    st.sidebar.markdown("---")  # Add a separator

    col1, col2 = st.sidebar.columns(2)

    with col1:
        if st.button("Backup Database"):
            with st.spinner("Creating backup..."):
                success, result = backup_database()
                if success:
                    st.success(f"Backup created successfully!\nFile: {result}")
                else:
                    st.error(f"Backup failed: {result}")

    with col2:
        # Get list of backup files
        backup_dir = "database_backups"
        if os.path.exists(backup_dir):
            backup_files = [f for f in os.listdir(backup_dir) if f.endswith(".sql")]
            if backup_files:
                selected_backup = st.selectbox(
                    "Select backup to restore",
                    backup_files,
                    format_func=lambda x: x.replace("backup_", "").replace(".sql", ""),
                )

                if st.button("Restore Database"):
                    if st.warning("⚠️ This will overwrite the current database. Are you sure?"):
                        with st.spinner("Restoring database..."):
                            success, result = restore_database(
                                os.path.join(backup_dir, selected_backup)
                            )
                            if success:
                                st.success("Database restored successfully!")
                            else:
                                st.error(f"Restore failed: {result}")
            else:
                st.info("No backup files found")
        else:
            st.info("Backup directory not found")


if __name__ == "__main__":
    main()
