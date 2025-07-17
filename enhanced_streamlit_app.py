# enhanced_streamlit_app.py
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from enhanced_agent import enhanced_assistant
import plotly.express as px
import plotly.graph_objects as go
import logging

# Configure logging for Streamlit app
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="🚚 AI Delivery Assistant Pro",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "selected_tab" not in st.session_state:
    st.session_state.selected_tab = "Chat"

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    /* Keeping these for potential future use with direct HTML rendering if needed */
    .status-preparing { color: #ff9800; }
    .status-in_transit { color: #2196f3; }
    .status-delivered { color: #4caf50; }
    .status-cancelled { color: #f44336; }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    /* Improve button styling */
    div.stButton > button:first-child {
        background-color: #764ba2;
        color: white;
        border-radius: 5px;
        border: none;
        padding: 10px 20px;
        font-size: 16px;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    div.stButton > button:first-child:hover {
        background-color: #667eea;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header"><h1>🚚 AI Delivery Assistant Pro</h1><p>Your intelligent food delivery companion</p></div>', unsafe_allow_html=True)

# Sidebar navigation
with st.sidebar:
    st.title("🎛️ Navigation")
    tab = st.radio("Select Tab", ["💬 Chat", "📊 Dashboard", "🔧 Admin Panel"])
    
    st.markdown("---")
    st.markdown("### 💡 Quick Actions")
    
    # Using st.form for quick actions to ensure proper state management and prevent re-runs
    with st.form("quick_actions_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            track_order_btn = st.form_submit_button("🔍 Track")
        with col2:
            cancel_order_btn = st.form_submit_button("❌ Cancel")
        with col3:
            recommendations_btn = st.form_submit_button("🍽️ Recommend")
        
        if track_order_btn:
            st.session_state.quick_action = "track_order"
        elif cancel_order_btn:
            st.session_state.quick_action = "cancel_order"
        elif recommendations_btn:
            st.session_state.quick_action = "recommendations"

    st.markdown("---")
    st.markdown("### 📝 Sample Queries")
    st.markdown("""
    - "Where is my order #1023?"
    - "Cancel order 2042"
    - "What goes well with pizza?"
    - "Show order history for John Doe"
    - "I want to rate order 1023 as 5 stars"
    - "Tell me about Mario's Pizza"
    """)

# Main content area
if tab == "💬 Chat":
    st.header("💬 Chat with AI Assistant")
    
    # Chat interface
    chat_container = st.container()
    
    with chat_container:
        # Display chat history
        for msg, is_user in st.session_state.chat_history:
            with st.chat_message("user" if is_user else "assistant"):
                st.markdown(msg)
    
    # Chat input
    user_input = st.chat_input("Ask me anything about your orders, food recommendations, or delivery...")
    
    # Handle quick actions by pre-filling the user_input if a quick action button was clicked
    if "quick_action" in st.session_state and st.session_state.quick_action:
        if st.session_state.quick_action == "track_order":
            user_input = "I want to track my order"
        elif st.session_state.quick_action == "cancel_order":
            user_input = "I want to cancel my order"
        elif st.session_state.quick_action == "recommendations":
            user_input = "I want food recommendations"
        # Clear the quick action after processing
        del st.session_state.quick_action 
        st.experimental_rerun() # Rerun to display the pre-filled prompt and get AI response

    # Process user input (either typed or from quick action)
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append((user_input, True))
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Get AI response
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

elif tab == "📊 Dashboard":
    st.header("📊 Delivery Dashboard")
    
    conn = None
    try:
        conn = sqlite3.connect(enhanced_assistant.db.db_path)
        
        # Orders overview
        orders_df = pd.read_sql_query("""
            SELECT order_id, customer_name, items, status, estimated_delivery, 
                   restaurant_name, order_total, created_at
            FROM orders
            ORDER BY created_at DESC
        """, conn)
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_orders = len(orders_df)
            st.markdown(f'<div class="metric-card"><h4>📦 Total Orders</h4><h2>{total_orders}</h2></div>', unsafe_allow_html=True)
        
        with col2:
            active_orders = len(orders_df[orders_df['status'].isin(['preparing', 'in_transit'])])
            st.markdown(f'<div class="metric-card"><h4>🚚 Active Orders</h4><h2>{active_orders}</h2></div>', unsafe_allow_html=True)
        
        with col3:
            delivered_orders = len(orders_df[orders_df['status'] == 'delivered'])
            st.markdown(f'<div class="metric-card"><h4>✅ Delivered</h4><h2>{delivered_orders}</h2></div>', unsafe_allow_html=True)
        
        with col4:
            total_revenue = orders_df['order_total'].sum() if not orders_df.empty else 0.0
            st.markdown(f'<div class="metric-card"><h4>💰 Total Revenue</h4><h2>${total_revenue:.2f}</h2></div>', unsafe_allow_html=True)
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Order status distribution
            if not orders_df.empty:
                status_counts = orders_df['status'].value_counts()
                fig_status = px.pie(
                    values=status_counts.values,
                    names=status_counts.index,
                    title="📈 Order Status Distribution"
                )
                st.plotly_chart(fig_status, use_container_width=True)
            else:
                st.info("No order data available for status distribution.")
        
        with col2:
            # Revenue by restaurant
            if not orders_df.empty:
                restaurant_revenue = orders_df.groupby('restaurant_name')['order_total'].sum().sort_values(ascending=False)
                fig_revenue = px.bar(
                    x=restaurant_revenue.index,
                    y=restaurant_revenue.values,
                    title="🏪 Revenue by Restaurant"
                )
                st.plotly_chart(fig_revenue, use_container_width=True)
            else:
                st.info("No order data available for revenue by restaurant.")
        
        # Orders table
        st.subheader("📋 Recent Orders")
        
        # Display orders table with enhanced status display
        display_df = orders_df.copy()
        display_df['status'] = display_df['status'].apply(lambda x: f"🔸 {x.title()}")
        # Also, format estimated_delivery for display
        display_df['estimated_delivery'] = pd.to_datetime(display_df['estimated_delivery']).dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(
            display_df[['order_id', 'customer_name', 'items', 'status', 'restaurant_name', 'order_total', 'estimated_delivery']],
            use_container_width=True,
            hide_index=True
        )
        
        # Feedback data
        feedback_df = pd.read_sql_query("""
            SELECT f.order_id, f.rating, f.comments, f.created_at, o.customer_name
            FROM feedback f
            JOIN orders o ON f.order_id = o.order_id
            ORDER BY f.created_at DESC
        """, conn)
        
        if not feedback_df.empty:
            st.subheader("⭐ Customer Feedback")
            
            # Average rating
            avg_rating = feedback_df['rating'].mean()
            st.metric("📊 Average Rating", f"{avg_rating:.1f}/5 ⭐")
            
            # Feedback distribution
            rating_counts = feedback_df['rating'].value_counts().sort_index()
            fig_ratings = px.bar(
                x=rating_counts.index,
                y=rating_counts.values,
                title="⭐ Rating Distribution",
                labels={"x": "Rating (Stars)", "y": "Number of Reviews"},
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig_ratings, use_container_width=True)
            
            # Recent feedback
            st.dataframe(
                feedback_df[['order_id', 'customer_name', 'rating', 'comments']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No customer feedback available yet.")
            
    except sqlite3.Error as e:
        logger.error(f"Dashboard database error: {e}")
        st.error(f"❌ Could not load dashboard data due to a database error: {e}")
    except Exception as e:
        logger.error(f"Dashboard unexpected error: {e}")
        st.error(f"❌ An unexpected error occurred while loading the dashboard: {e}")
    finally:
        if conn:
            conn.close()

elif tab == "🔧 Admin Panel":
    st.header("🔧 Admin Panel")
    
    # Database management
    st.subheader("🗄️ Database Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📦 Add New Order")
        with st.form("add_order"):
            order_id = st.number_input("Order ID", min_value=1, value=1000 + len(pd.read_sql_query("SELECT order_id FROM orders", sqlite3.connect(enhanced_assistant.db.db_path)).index), help="Unique Order ID")
            customer_name = st.text_input("Customer Name", help="Name of the customer")
            items = st.text_input("Items (comma-separated)", help="e.g., Margherita Pizza, Garlic Bread")
            status = st.selectbox("Status", ["preparing", "in_transit", "delivered", "cancelled"], help="Current status of the order")
            restaurant_name = st.text_input("Restaurant Name", help="Name of the restaurant")
            delivery_address = st.text_input("Delivery Address", help="Full delivery address")
            phone_number = st.text_input("Phone Number", help="Customer's phone number")
            order_total = st.number_input("Order Total", min_value=0.0, step=0.01, help="Total cost of the order")
            
            if st.form_submit_button("Add Order"):
                conn = None
                try:
                    conn = sqlite3.connect(enhanced_assistant.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO orders (order_id, customer_name, items, status, restaurant_name, 
                                          delivery_address, phone_number, order_total, estimated_delivery)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (order_id, customer_name, items, status, restaurant_name, 
                          delivery_address, phone_number, order_total, (datetime.now() + timedelta(minutes=30)).isoformat())) # Default ETA
                    conn.commit()
                    st.success(f"✅ Order {order_id} added successfully!")
                except sqlite3.IntegrityError:
                    st.error(f"❌ Error: Order ID {order_id} already exists. Please choose a different ID.")
                except sqlite3.Error as e:
                    logger.error(f"Admin: Error adding order: {e}")
                    st.error(f"❌ Error adding order: {e}")
                except Exception as e:
                    logger.error(f"Admin: Unexpected error adding order: {e}")
                    st.error(f"❌ An unexpected error occurred: {e}")
                finally:
                    if conn:
                        conn.close()
    
    with col2:
        st.markdown("### 🍽️ Add Menu Item")
        with st.form("add_menu_item"):
            item_name = st.text_input("Item Name", help="Name of the menu item")
            category = st.text_input("Category", help="e.g., Pizza, Burger, Pasta")
            price = st.number_input("Price", min_value=0.0, step=0.01, help="Price of the item")
            description = st.text_area("Description", help="Detailed description of the item")
            pairings = st.text_input("Recommended Pairings (comma-separated)", help="e.g., Fries, Coke")
            
            if st.form_submit_button("Add Menu Item"):
                conn = None
                try:
                    conn = sqlite3.connect(enhanced_assistant.db.db_path)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO menu_items (name, category, price, description, recommended_pairings)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (item_name, category, price, description, pairings))
                    conn.commit()
                    st.success(f"✅ Menu item '{item_name}' added successfully!")
                except sqlite3.Error as e:
                    logger.error(f"Admin: Error adding menu item: {e}")
                    st.error(f"❌ Error adding menu item: {e}")
                except Exception as e:
                    logger.error(f"Admin: Unexpected error adding menu item: {e}")
                    st.error(f"❌ An unexpected error occurred: {e}")
                finally:
                    if conn:
                        conn.close()
    
    # System status
    st.subheader("⚙️ System Status")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card"><h4>🤖 AI Model</h4><h3>Mistral (Ollama)</h3></div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card"><h4>💾 Database Type</h4><h3>SQLite</h3></div>', unsafe_allow_html=True)
    
    with col3:
        conn = None
        try:
            # Test database connection
            conn = sqlite3.connect(enhanced_assistant.db.db_path)
            conn.close()
            st.markdown('<div class="metric-card"><h4>📊 Database Status</h4><h3 style="color:#4caf50;">✅ Connected</h3></div>', unsafe_allow_html=True)
        except Exception as e:
            logger.error(f"Database connection test failed in Admin: {e}")
            st.markdown('<div class="metric-card"><h4>📊 Database Status</h4><h3 style="color:#f44336;">❌ Error</h3></div>', unsafe_allow_html=True)
        finally:
            if conn:
                conn.close()
    
    # Clear chat history button
    st.markdown("---")
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.success("✅ Chat history cleared!")

# Footer
st.markdown("---")
st.markdown("### 🚀 Features")
st.markdown("""
- 💬 **AI Chat Assistant**: Get instant answers and assistance with your orders.
- 🔍 **Real-time Order Tracking**: Track your orders with live updates.
- ❌ **Order Cancellation**: Cancel orders with automatic refund processing.
- 🍽️ **Personalized Recommendations**: Discover new dishes and perfect pairings.
- 📋 **Order History**: View your past orders quickly.
- ⭐ **Customer Feedback**: Easily submit ratings and comments for your orders.
- 📊 **Delivery Dashboard**: Visual insights into order statuses, revenue, and feedback.
- 🔧 **Admin Panel**: Manage orders and menu items directly (for internal use).
""")
