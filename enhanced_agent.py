# enhanced_agent.py
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from langchain_community.llms import Ollama
from langchain.agents import initialize_agent, Tool
from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Handles all database operations for the delivery assistant"""
    
    def __init__(self, db_path: str = "delivery_assistant.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Orders table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id INTEGER PRIMARY KEY,
                    customer_name TEXT NOT NULL,
                    items TEXT NOT NULL,
                    status TEXT NOT NULL,
                    estimated_delivery TIMESTAMP,
                    restaurant_name TEXT,
                    delivery_address TEXT,
                    phone_number TEXT,
                    order_total REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Menu items table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS menu_items (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    price REAL NOT NULL,
                    description TEXT,
                    recommended_pairings TEXT
                )
            ''')
            
            # Customer feedback table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER,
                    rating INTEGER,
                    comments TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders (order_id)
                )
            ''')
            
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
        finally:
            if conn:
                conn.close()
        
        # Populate with sample data
        self.populate_sample_data()
    
    def populate_sample_data(self):
        """Add sample orders and menu items for testing"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if data already exists
            cursor.execute("SELECT COUNT(*) FROM orders")
            if cursor.fetchone()[0] > 0:
                return # Data already exists, no need to populate
            
            # Sample orders
            sample_orders = [
                (1023, "John Doe", "Margherita Pizza, Garlic Bread", "in_transit", 
                 (datetime.now() + timedelta(minutes=15)).isoformat(), "Mario's Pizza", "123 Main St", "555-0123", 24.99),
                (2042, "Jane Smith", "Cheeseburger, Fries, Coke", "preparing", 
                 (datetime.now() + timedelta(minutes=25)).isoformat(), "Burger Palace", "456 Oak Ave", "555-0456", 18.50),
                (3051, "Bob Johnson", "Chicken Alfredo, Caesar Salad", "delivered", 
                 (datetime.now() - timedelta(minutes=30)).isoformat(), "Pasta House", "789 Pine Rd", "555-0789", 22.75),
            ]
            
            cursor.executemany('''
                INSERT INTO orders (order_id, customer_name, items, status, estimated_delivery, 
                                  restaurant_name, delivery_address, phone_number, order_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', sample_orders)
            
            # Sample menu items
            sample_menu = [
                ("Margherita Pizza", "Pizza", 18.99, "Classic tomato sauce, mozzarella, basil", "Garlic Bread, Caesar Salad, Red Wine"),
                ("Cheeseburger", "Burger", 12.99, "Beef patty, cheese, lettuce, tomato", "Fries, Onion Rings, Milkshake"),
                ("Chicken Alfredo", "Pasta", 16.99, "Grilled chicken, creamy alfredo sauce", "Garlic Bread, House Salad, White Wine"),
                ("Caesar Salad", "Salad", 8.99, "Romaine lettuce, croutons, parmesan", "Soup, Breadsticks, Iced Tea"),
            ]
            
            cursor.executemany('''
                INSERT INTO menu_items (name, category, price, description, recommended_pairings)
                VALUES (?, ?, ?, ?, ?)
            ''', sample_menu)
            
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Sample data population error: {e}")
        finally:
            if conn:
                conn.close()

class EnhancedDeliveryAssistant:
    """Enhanced delivery assistant with database integration and improved functionality"""
    
    def __init__(self):
        self.db = DatabaseManager()
        # Initialize Ollama model, ensure it's running
        self.llm = Ollama(model="mistral")
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.agent = self._create_agent()
    
    def track_order(self, order_id: str) -> str:
        """Enhanced order tracking with real database lookup"""
        try:
            order_id = int(order_id)
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT order_id, customer_name, items, status, estimated_delivery, 
                       restaurant_name, delivery_address 
                FROM orders WHERE order_id = ?
            ''', (order_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return f"❌ Order #{order_id} not found. Please check your order ID."
            
            order_id, customer_name, items, status, est_delivery_str, restaurant, address = result
            
            status_messages = {
                "preparing": "🍳 Your order is being prepared",
                "in_transit": "🚚 Your order is on the way",
                "delivered": "✅ Your order has been delivered",
                "cancelled": "❌ Your order was cancelled"
            }
            
            est_time = None
            if est_delivery_str:
                try:
                    est_time = datetime.fromisoformat(est_delivery_str)
                except ValueError:
                    logger.warning(f"Could not parse estimated_delivery: {est_delivery_str}")
                    # Handle cases where format might be different, e.g., if stored as a simple string
                    pass

            time_msg = ""
            if est_time and status != "delivered":
                time_remaining = est_time - datetime.now()
                if time_remaining.total_seconds() > 0:
                    minutes = int(time_remaining.total_seconds() / 60)
                    time_msg = f" - ETA: {minutes} minutes"
                else:
                    time_msg = " - Should arrive any moment!"
            
            return f"""📦 Order #{order_id} Status Update:
{status_messages.get(status, status).title()}{time_msg}
🏪 Restaurant: {restaurant}
📍 Delivery to: {address}
🍽️ Items: {items}"""
            
        except ValueError:
            return "❌ Please provide a valid order ID number."
        except sqlite3.Error as e:
            logger.error(f"Database error tracking order {order_id}: {e}")
            return "❌ Sorry, there was a database error tracking your order. Please try again."
        except Exception as e:
            logger.error(f"Unexpected error tracking order {order_id}: {e}")
            return "❌ Sorry, I couldn't track your order right now due to an unexpected issue. Please try again."
    
    def cancel_order(self, order_id: str = None) -> str:
        """Enhanced order cancellation with database updates"""
        if not order_id:
            return "⚠️ I need an order ID to cancel your order. Please provide your order number."
        
        try:
            order_id = int(order_id)
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Check if order exists and its current status
            cursor.execute('SELECT status, customer_name, order_total FROM orders WHERE order_id = ?', (order_id,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return f"❌ Order #{order_id} not found. Please check your order ID."
            
            status, customer_name, order_total = result
            
            if status == "delivered":
                conn.close()
                return f"❌ Order #{order_id} has already been delivered and cannot be cancelled."
            
            if status == "cancelled":
                conn.close()
                return f"ℹ️ Order #{order_id} was already cancelled."
            
            # Update order status to cancelled
            cursor.execute('UPDATE orders SET status = ? WHERE order_id = ?', ("cancelled", order_id))
            conn.commit()
            conn.close()
            
            return f"""✅ Order #{order_id} has been successfully cancelled!
💰 Refund of ${order_total:.2f} will be processed within 3-5 business days.
📧 You'll receive a confirmation email shortly."""
            
        except ValueError:
            return "❌ Please provide a valid order ID number."
        except sqlite3.Error as e:
            logger.error(f"Database error cancelling order {order_id}: {e}")
            return "❌ Sorry, there was a database error cancelling your order. Please try again."
        except Exception as e:
            logger.error(f"Unexpected error cancelling order {order_id}: {e}")
            return "❌ Sorry, I couldn't cancel your order right now due to an unexpected issue. Please try again."
    
    def get_menu_recommendation(self, food_item: str) -> str:
        """Enhanced menu recommendations using database"""
        conn = None
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Search for the food item in the database
            # Using UNION ALL to search in both name and description, prioritizing name matches implicitly
            cursor.execute('''
                SELECT name, price, description, recommended_pairings 
                FROM menu_items 
                WHERE name LIKE ? 
                UNION ALL 
                SELECT name, price, description, recommended_pairings 
                FROM menu_items 
                WHERE description LIKE ? AND name NOT LIKE ?
                LIMIT 1
            ''', (f"%{food_item}%", f"%{food_item}%", f"%{food_item}%"))
            
            result = cursor.fetchone() # Fetch just one result
            
            if result:
                name, price, description, pairings = result
                return f"""🍽️ {name} (${price:.2f})
📝 {description}
🤝 Great pairings: {pairings}"""
            else:
                # Fallback to original logic if no database match
                food_item_lower = food_item.lower()
                if "burger" in food_item_lower:
                    return "🍔 For a burger, we recommend a side of curly fries and a cold soda or milkshake!"
                elif "pizza" in food_item_lower:
                    return "🍕 Pizza goes great with garlic knots and sparkling water or a nice red wine!"
                elif "pasta" in food_item_lower:
                    return "🍝 Try a house salad and a glass of white wine with pasta dishes!"
                else:
                    return f"🍽️ For {food_item}, we suggest asking our chef for the perfect drink pairing!"
                    
        except sqlite3.Error as e:
            logger.error(f"Database error getting menu recommendation for '{food_item}': {e}")
            return "❌ Sorry, there was a database error getting recommendations. Please try again."
        except Exception as e:
            logger.error(f"Unexpected error getting menu recommendation for '{food_item}': {e}")
            return "❌ Sorry, I couldn't get recommendations right now due to an unexpected issue. Please try again."
        finally:
            if conn:
                conn.close()
    
    def get_order_history(self, customer_name: str) -> str:
        """Get order history for a customer"""
        conn = None
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT order_id, items, status, order_total, created_at
                FROM orders WHERE customer_name LIKE ?
                ORDER BY created_at DESC LIMIT 5
            ''', (f"%{customer_name}%",))
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                return f"❌ No orders found for {customer_name}."
            
            history = f"📋 Order History for {customer_name}:\n"
            for order_id, items, status, total, created in results:
                try:
                    created_date = datetime.fromisoformat(created).strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    created_date = created # Fallback if not isoformat
                history += f"\n🔸 Order #{order_id} ({created_date})\n   Items: {items}\n   Status: {status.title()}\n   Total: ${total:.2f}\n"
            
            return history
            
        except sqlite3.Error as e:
            logger.error(f"Database error getting order history for '{customer_name}': {e}")
            return "❌ Sorry, there was a database error retrieving order history. Please try again."
        except Exception as e:
            logger.error(f"Unexpected error getting order history for '{customer_name}': {e}")
            return "❌ Sorry, I couldn't retrieve order history right now due to an unexpected issue."
        finally:
            if conn:
                conn.close()
    
    def submit_feedback(self, order_id: str, rating: str, comments: str = "") -> str:
        """Submit feedback for an order"""
        conn = None
        try:
            order_id_int = int(order_id)
            rating_int = int(rating)
            
            if rating_int < 1 or rating_int > 5:
                return "❌ Please provide a rating between 1 and 5 stars."
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Check if order exists
            cursor.execute('SELECT order_id FROM orders WHERE order_id = ?', (order_id_int,))
            if not cursor.fetchone():
                conn.close()
                return f"❌ Order #{order_id_int} not found."
            
            # Insert feedback
            cursor.execute('''
                INSERT INTO feedback (order_id, rating, comments)
                VALUES (?, ?, ?)
            ''', (order_id_int, rating_int, comments))
            
            conn.commit()
            conn.close()
            
            stars = "⭐" * rating_int
            return f"✅ Thank you for your feedback!\n{stars} ({rating_int}/5)\nOrder #{order_id_int}: {comments}"
            
        except ValueError:
            return "❌ Please provide valid order ID and rating (1-5)."
        except sqlite3.Error as e:
            logger.error(f"Database error submitting feedback for order {order_id}: {e}")
            return "❌ Sorry, there was a database error submitting your feedback. Please try again."
        except Exception as e:
            logger.error(f"Unexpected error submitting feedback for order {order_id}: {e}")
            return "❌ Sorry, I couldn't submit your feedback right now due to an unexpected issue."
        finally:
            if conn:
                conn.close()
    
    def get_restaurant_info(self, restaurant_name: str) -> str:
        """Get information about restaurants"""
        conn = None
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT DISTINCT restaurant_name, COUNT(*) as order_count
                FROM orders WHERE restaurant_name LIKE ?
                GROUP BY restaurant_name
            ''', (f"%{restaurant_name}%",))
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                return f"❌ No information found for '{restaurant_name}'."
            
            info = "🏪 Restaurant Information:\n"
            for restaurant, count in results:
                info += f"\n📍 {restaurant}\n🛍️ Total orders: {count}\n"
            
            return info
            
        except sqlite3.Error as e:
            logger.error(f"Database error getting restaurant info for '{restaurant_name}': {e}")
            return "❌ Sorry, there was a database error retrieving restaurant information. Please try again."
        except Exception as e:
            logger.error(f"Unexpected error getting restaurant info for '{restaurant_name}': {e}")
            return "❌ Sorry, I couldn't get restaurant information right now due to an unexpected issue."
        finally:
            if conn:
                conn.close()
    
    def _create_agent(self):
        """Create the LangChain agent with enhanced tools"""
        tools = [
            Tool(
                name="track_order",
                func=self.track_order,
                description="Track the current location and ETA for a given order ID. Input should be the order ID number."
            ),
            Tool(
                name="cancel_order",
                func=self.cancel_order,
                description="Cancel an order by ID. Input should be the order ID number."
            ),
            Tool(
                name="get_menu_recommendation",
                func=self.get_menu_recommendation,
                description="Get menu recommendations and pairings for a food item. Input should be the food item name."
            ),
            Tool(
                name="get_order_history",
                func=self.get_order_history,
                description="Get order history for a customer. Input should be the customer name."
            ),
            Tool(
                name="submit_feedback",
                # The agent will pass arguments as a single string, so split it
                func=lambda x: self.submit_feedback(*x.split(',', 2)), 
                description="Submit feedback for an order. Input should be 'order_id,rating,comments' (comments optional). For example: '1023,5,Great food!'"
            ),
            Tool(
                name="get_restaurant_info",
                func=self.get_restaurant_info,
                description="Get information about a restaurant. Input should be the restaurant name."
            )
        ]
        
        return initialize_agent(
            tools=tools,
            llm=self.llm,
            agent_type="zero-shot-react-description",
            verbose=True,
            memory=self.memory,
            handle_parsing_errors=True
        )
    
    def run(self, query: str) -> str:
        """Run the agent with the given query"""
        try:
            return self.agent.run(query)
        except Exception as e:
            logger.error(f"Error running agent with query '{query}': {e}")
            return "❌ Sorry, I encountered an error. Please try rephrasing your question or contact support if the issue persists."

# Create global instance
enhanced_assistant = EnhancedDeliveryAssistant()

# CLI mode for testing
if __name__ == "__main__":
    print("🚚 Enhanced AI Delivery Assistant")
    print("Available commands:")
    print("- Track order: 'Where is my order 1023?'")
    print("- Cancel order: 'Cancel order 2042'")
    print("- Get recommendations: 'What goes well with pizza?'")
    print("- Order history: 'Show my order history for John Doe'")
    print("- Submit feedback: 'I want to rate order 1023 as 5 stars, great food!'")
    print("- Restaurant info: 'Tell me about Mario's Pizza'")
    print("\nType 'exit' or 'quit' to end.\n")
    
    while True:
        user_query = input("User: ")
        if user_query.lower() in ["exit", "quit"]:
            break
        print("AI:", enhanced_assistant.run(user_query))
