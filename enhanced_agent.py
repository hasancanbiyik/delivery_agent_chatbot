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
                (1023, "John Doe", "Margherita Pizza", "in_transit", 
                 (datetime.now() + timedelta(minutes=15)).isoformat(), "Mario's Pizza", "123 Main St, Totowa", "555-0123", 18.99),
                (2042, "Jane Smith", "Cheeseburger, Fries", "preparing", 
                 (datetime.now() + timedelta(minutes=25)).isoformat(), "Burger Palace", "456 Oak Ave, Totowa", "555-0456", 16.98),
                (3051, "Bob Johnson", "Chicken Alfredo", "delivered", 
                 (datetime.now() - timedelta(minutes=30)).isoformat(), "Pasta House", "789 Pine Rd, Totowa", "555-0789", 16.99),
            ]
            
            cursor.executemany('''
                INSERT INTO orders (order_id, customer_name, items, status, estimated_delivery, 
                                  restaurant_name, delivery_address, phone_number, order_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', sample_orders)
            
            # Sample menu items
            sample_menu = [
                ("Margherita Pizza", "Pizza", 18.99, "Classic tomato sauce, mozzarella, basil", "Garlic Bread, Diet Coke, Red Wine"),
                ("Cheeseburger", "Burger", 12.99, "Beef patty, cheese, lettuce, tomato", "Onion Rings, Milkshake, Extra Fries"),
                ("Chicken Alfredo", "Pasta", 16.99, "Grilled chicken, creamy alfredo sauce", "House Salad, White Wine, Breadsticks"),
                ("Caesar Salad", "Salad", 8.99, "Romaine lettuce, croutons, parmesan", "Soup, Iced Tea"),
                ("Garlic Bread", "Side", 5.99, "Toasted bread with garlic butter", "Marinara Sauce"),
                ("Fries", "Side", 3.99, "Crispy golden fries", "Ketchup"),
                ("Diet Coke", "Drink", 2.50, "A refreshing diet soda", "N/A"),
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
    """An owner-oriented assistant for managing restaurant orders."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.llm = Ollama(model="mistral")
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        self.agent = self._create_agent()
    
    # MODIFIED: This tool now proactively suggests upsells.
    def track_order(self, order_id: str) -> str:
        """Tracks an order and suggests potential upsells based on the items."""
        try:
            order_id_int = int(order_id)
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT items, status FROM orders WHERE order_id = ?', (order_id_int,))
            order_result = cursor.fetchone()
            
            if not order_result:
                conn.close()
                return f"❌ Order #{order_id} not found. Please check the order ID."
            
            items_str, status = order_result
            status_msg = status.replace('_', ' ')
            
            # Find pairings for the first item in the order
            first_item = items_str.split(',')[0].strip()
            cursor.execute('SELECT recommended_pairings FROM menu_items WHERE name = ?', (first_item,))
            pairings_result = cursor.fetchone()
            conn.close()
            
            response = f"Order #{order_id} is currently **{status_msg}**. The customer ordered: **{items_str}**."
            
            if pairings_result and pairings_result[0]:
                response += f"\n\n📈 **Upsell Opportunity**: You could recommend adding one of the following: **{pairings_result[0]}**. \nTo add an item, ask me to 'add [item name] to order #{order_id}'."
            else:
                response += "\n\nNo specific pairings found for the items in this order."
            
            return response
            
        except ValueError:
            return "❌ Please provide a valid order ID number."
        except Exception as e:
            logger.error(f"Error in track_order: {e}")
            return "❌ An unexpected error occurred while tracking the order."

    # NEW: Tool to update an order with a new item.
    def update_order_with_recommendation(self, order_id: str, item_to_add: str) -> str:
        """Adds a recommended item to an existing order and updates the total."""
        try:
            order_id_int = int(order_id)
            item_name = item_to_add.strip()
            
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Get the new item's price
            cursor.execute('SELECT price FROM menu_items WHERE name LIKE ?', (f'%{item_name}%',))
            item_result = cursor.fetchone()
            if not item_result:
                conn.close()
                return f"❌ Item '{item_name}' not found in the menu."
            item_price = item_result[0]
            
            # Get the current order details
            cursor.execute('SELECT items, order_total FROM orders WHERE order_id = ?', (order_id_int,))
            order_result = cursor.fetchone()
            if not order_result:
                conn.close()
                return f"❌ Order #{order_id_int} not found."
            current_items, current_total = order_result
            
            # Update the order
            new_items = f"{current_items}, {item_name}"
            new_total = current_total + item_price
            cursor.execute('UPDATE orders SET items = ?, order_total = ? WHERE order_id = ?', (new_items, new_total, order_id_int))
            conn.commit()
            conn.close()
            
            return f"✅ Success! I have added **{item_name}** to order #{order_id_int}. The new total is **${new_total:.2f}**. The customer has been notified."
            
        except ValueError:
            return "❌ Please provide a valid order ID."
        except Exception as e:
            logger.error(f"Error in update_order: {e}")
            return "❌ An unexpected error occurred while updating the order."
    
    def cancel_order(self, order_id: str = None) -> str:
        """Cancels an entire order."""
        if not order_id:
            return "⚠️ I need an order ID to cancel an order."
        try:
            order_id = int(order_id)
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT status FROM orders WHERE order_id = ?', (order_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                return f"❌ Order #{order_id} not found."
            if result[0] in ["delivered", "cancelled"]:
                conn.close()
                return f"❌ Order #{order_id} cannot be cancelled as it is already {result[0]}."
            
            cursor.execute('UPDATE orders SET status = ? WHERE order_id = ?', ("cancelled", order_id))
            conn.commit()
            conn.close()
            return f"✅ Order #{order_id} has been successfully cancelled."
        except ValueError:
            return "❌ Please provide a valid order ID number."
        except Exception as e:
            logger.error(f"Error in cancel_order: {e}")
            return "❌ An unexpected error occurred while cancelling the order."

    def get_order_history(self, customer_name: str) -> str:
        """Gets the order history for a specific customer."""
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
            return f"❌ No orders found for a customer named '{customer_name}'."
        history = f"📋 Order History for {customer_name}:\n"
        for order_id, items, status, total, created in results:
            created_date = datetime.fromisoformat(created).strftime("%Y-%m-%d %H:%M")
            history += f"\n- Order #{order_id} ({created_date}): {items} - Status: {status} - Total: ${total:.2f}"
        return history

    def _create_agent(self):
        """Creates the LangChain agent with owner-oriented tools."""
        tools = [
            Tool(
                name="track_order_with_upsell_suggestions",
                func=self.track_order,
                description="Use this to check the status of a specific order. The input must be the numerical order ID. This tool also provides upsell recommendations."
            ),
            # NEW Tool added to the agent
            Tool(
                name="update_order_with_new_item",
                func=lambda x: self.update_order_with_recommendation(*x.split(',', 1)),
                description="Use this to add a new item to an existing order. The input should be a string with the order ID and the item name, separated by a comma. For example: '1023,Diet Coke'."
            ),
            Tool(
                name="cancel_order",
                func=self.cancel_order,
                description="Use this to cancel an entire order. The input must be the numerical order ID."
            ),
            Tool(
                name="get_customer_order_history",
                func=self.get_order_history,
                description="Use this to get the order history for a customer. The input must be the customer's name."
            ),
        ]
        
        # Define a prompt that frames the agent as an assistant for a restaurant owner
        agent_prompt = """You are an AI assistant for a restaurant owner. Your goal is to help the owner manage orders, identify upsell opportunities, and handle customer information efficiently. When responding, be concise and professional.

        You have access to the following tools:"""

        return initialize_agent(
            tools=tools,
            llm=self.llm,
            agent="zero-shot-react-description",
            verbose=True,
            memory=self.memory,
            handle_parsing_errors=True,
            agent_kwargs={"prefix": agent_prompt}
        )
    
    def run(self, query: str) -> str:
        """Run the agent with the given query"""
        try:
            return self.agent.run(query)
        except Exception as e:
            logger.error(f"Error running agent with query '{query}': {e}")
            return "❌ Sorry, I encountered an error. Please try rephrasing your question."

# Create global instance
enhanced_assistant = EnhancedDeliveryAssistant()
