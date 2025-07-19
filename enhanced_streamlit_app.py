# enhanced_streamlit_app.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from enhanced_agent import enhanced_assistant
import plotly.express as px
import logging

# Configure logging for Streamlit app
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="🚚 Restaurant Management Assistant",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #0061ff 0%, #60efff 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #0061ff;
        margin: 0.5rem 0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    div.stButton > button:first-child {
        background-color: #0061ff;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header"><h1>🏪 Restaurant Management Assistant</h1><p>Your intelligent tool for order management and growth</p></div>', unsafe_allow_html=True)

# Sidebar navigation
with st.sidebar:
    st.title("🎛️ Navigation")
    # NEW: Added "Menu" to the list of tabs
    tab = st.radio("Select Tab", ["💬 Assistant Chat", "🍽️ Menu", "📊 Dashboard", "🔧 Admin Panel"])
    
    st.markdown("---")
    st.markdown("### 💡 Quick Actions")
    
    with st.form("quick_actions_form"):
        col1, col2 = st.columns(2)
        with col1:
            track_order_btn = st.form_submit_button("🔍 Track")
        with col2:
            cancel_order_btn = st.form_submit_button("❌ Cancel")
        
        if track_order_btn:
            st.session_state.quick_action = "track_order"
        elif cancel_order_btn:
            st.session_state.quick_action = "cancel_order"

    st.markdown("---")
    st.markdown("### 📝 Sample Prompts")
    st.markdown("""
    - "What is the status of order 1023?"
    - "Add Diet Coke to order 1023"
    - "Show me the order history for Jane Smith"
    - "Cancel order 2042"
    """)

# Main content area
if tab == "💬 Assistant Chat":
    st.header("💬 Chat with Your Assistant")
    
    chat_container = st.container()
    with chat_container:
        for msg, is_user in st.session_state.chat_history:
            with st.chat_message("user" if is_user else "assistant"):
                st.markdown(msg)
    
    user_input = st.chat_input("Ask about an order status, customer history, or updates...")
    
    if "quick_action" in st.session_state and st.session_state.quick_action:
        if st.session_state.quick_action == "track_order":
            user_input = "What is the status of order..."
        elif st.session_state.quick_action == "cancel_order":
            user_input = "Cancel order..."
        del st.session_state.quick_action 
        st.rerun()

    if user_input:
        st.session_state.chat_history.append((user_input, True))
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = enhanced_assistant.run(user_input)
                    st.markdown(response)
                    st.session_state.chat_history.append((response, False))
                except Exception as e:
                    error_msg = f"❌ Sorry, I encountered an error: {str(e)}"
                    logger.error(f"Streamlit chat error: {e}")
                    st.error(error_msg)
                    st.session_state.chat_history.append((error_msg, False))
        st.rerun()

# NEW: Logic for the Menu tab
elif tab == "🍽️ Menu":
    st.header("🍽️ Restaurant Menu")
    st.markdown("View all available menu items and their details. Add new items in the **Admin Panel**.")
    
    try:
        with sqlite3.connect(enhanced_assistant.db.db_path) as conn:
            menu_df = pd.read_sql_query("SELECT name, category, price, description, recommended_pairings FROM menu_items ORDER BY category, name", conn)
            
            # Rename columns for better display
            column_renames = {
                'name': 'Item Name',
                'category': 'Category',
                'price': 'Price ($)',
                'description': 'Description',
                'recommended_pairings': 'Recommended Pairings'
            }
            menu_df = menu_df.rename(columns=column_renames)
            
            st.dataframe(menu_df, use_container_width=True, hide_index=True)
            
    except Exception as e:
        logger.error(f"Menu Tab Error: {e}")
        st.error(f"❌ Could not load menu items: {e}")

elif tab == "📊 Dashboard":
    st.header("📊 Delivery Dashboard")
    conn = None
    try:
        conn = sqlite3.connect(enhanced_assistant.db.db_path)
        orders_df = pd.read_sql_query("SELECT * FROM orders ORDER BY created_at DESC", conn)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="metric-card"><h4>📦 Total Orders</h4><h2>{len(orders_df)}</h2></div>', unsafe_allow_html=True)
        with col2:
            active_orders = len(orders_df[orders_df['status'].isin(['preparing', 'in_transit'])])
            st.markdown(f'<div class="metric-card"><h4>🚚 Active Orders</h4><h2>{active_orders}</h2></div>', unsafe_allow_html=True)
        with col3:
            delivered_orders = len(orders_df[orders_df['status'] == 'delivered'])
            st.markdown(f'<div class="metric-card"><h4>✅ Delivered</h4><h2>{delivered_orders}</h2></div>', unsafe_allow_html=True)
        with col4:
            total_revenue = orders_df['order_total'].sum() if not orders_df.empty else 0.0
            st.markdown(f'<div class="metric-card"><h4>💰 Total Revenue</h4><h2>${total_revenue:.2f}</h2></div>', unsafe_allow_html=True)
        
        st.subheader("📋 Recent Orders")
        st.dataframe(orders_df, use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.error(f"Failed to load dashboard: {e}")
    finally:
        if conn:
            conn.close()

elif tab == "🔧 Admin Panel":
    st.header("🔧 Admin Panel")
    st.subheader("🗄️ Database Management")
    col1, col2 = st.columns(2)
    
    with col1:
        with st.form("add_order"):
            st.markdown("### 📦 Add New Order")
            order_id = st.number_input("Order ID", min_value=1, value=int(datetime.now().timestamp() % 100000))
            customer_name = st.text_input("Customer Name")
            items = st.text_input("Items (comma-separated)")
            status = st.selectbox("Status", ["preparing", "in_transit", "delivered", "cancelled"])
            restaurant_name = st.text_input("Restaurant Name", value="My Restaurant")
            delivery_address = st.text_input("Delivery Address")
            phone_number = st.text_input("Phone Number")
            order_total = st.number_input("Order Total", min_value=0.0, step=0.01)
            
            if st.form_submit_button("Add Order"):
                with sqlite3.connect(enhanced_assistant.db.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO orders (order_id, customer_name, items, status, restaurant_name, 
                                          delivery_address, phone_number, order_total, estimated_delivery)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (order_id, customer_name, items, status, restaurant_name, 
                          delivery_address, phone_number, order_total, (datetime.now() + timedelta(minutes=30)).isoformat()))
                    conn.commit()
                    st.success(f"✅ Order #{order_id} added successfully!")
    
    with col2:
        with st.form("add_menu_item"):
            st.markdown("### 🍽️ Add Menu Item")
            item_name = st.text_input("Item Name", help="Name of the menu item")
            category = st.text_input("Category", help="e.g., Pizza, Burger, Side, Drink")
            price = st.number_input("Price", min_value=0.0, format="%.2f", step=0.01, help="Price of the item")
            description = st.text_area("Description", help="Detailed description of the item")
            pairings = st.text_input("Recommended Pairings (comma-separated)", help="e.g., Fries, Coke")
            
            # IMPLEMENTED: Logic to add a menu item to the database
            if st.form_submit_button("Add Menu Item"):
                if not all([item_name, category, price]):
                    st.warning("Please fill in at least Item Name, Category, and Price.")
                else:
                    try:
                        with sqlite3.connect(enhanced_assistant.db.db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                INSERT INTO menu_items (name, category, price, description, recommended_pairings)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (item_name, category, price, description, pairings))
                            conn.commit()
                            st.success(f"✅ Menu item '{item_name}' added successfully!")
                    except sqlite3.Error as e:
                        logger.error(f"Admin: Error adding menu item: {e}")
                        st.error(f"❌ Error adding menu item to database: {e}")
