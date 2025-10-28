from typing import List
import json
from hd_google_hackathon.domain.order import Order, OrderItem
from hd_google_hackathon.data.repositories.order_repository import OrderRepository
from hd_google_hackathon.mock_db import connect_db

class SqliteOrderRepository(OrderRepository):
    def get_orders_for_dealer(self, dealer_id: str) -> List[Order]:
        conn = connect_db(read_only=True)
        cur = conn.cursor()
        cur.execute("""
            SELECT o.id, o.dealer_id, o.status, o.shipment_priority, o.history
            FROM orders o
            WHERE o.dealer_id = ?
        """, (dealer_id,))
        order_rows = cur.fetchall()

        orders = []
        for row in order_rows:
            order_id = row[0]
            cur.execute("""
                SELECT oi.dealer_product_id, oi.quantity
                FROM order_items oi
                WHERE oi.order_id = ?
            """, (order_id,))
            item_rows = cur.fetchall()
            items = [OrderItem(dealer_product_id=item[0], quantity=item[1]) for item in item_rows]
            
            history_str = row[4]
            history = json.loads(history_str) if history_str else []

            orders.append(Order(
                id=row[0],
                dealer_id=row[1],
                status=row[2],
                shipment_priority=row[3],
                items=items,
                history=history,
            ))
        
        conn.close()
        return orders

    def get_order_by_id(self, order_id: str, tenant_id: str) -> Order | None:
        conn = connect_db(read_only=True)
        cur = conn.cursor()
        cur.execute("""
            SELECT o.id, o.dealer_id, o.status, o.shipment_priority, o.history
            FROM orders o
            WHERE o.id = ?
        """, (order_id,))
        row = cur.fetchone()

        if row is None:
            return None

        cur.execute("""
            SELECT oi.dealer_product_id, oi.quantity
            FROM order_items oi
            WHERE oi.order_id = ?
        """, (order_id,))
        item_rows = cur.fetchall()
        items = [OrderItem(dealer_product_id=item[0], quantity=item[1]) for item in item_rows]
        
        history_str = row[4]
        history = json.loads(history_str) if history_str else []

        order = Order(
            id=row[0],
            dealer_id=row[1],
            status=row[2],
            shipment_priority=row[3],
            items=items,
            history=history,
        )
        
        conn.close()
        return order

    def get_orders_by_dealer(self, dealer_id: str, tenant_id: str) -> List[Order]:
        return self.get_orders_for_dealer(dealer_id)

    def update_order_status(self, order_id: str, status: str, tenant_id: str) -> Order | None:
        pass

    def create_order(self, dealer_id: str, items: List[dict], tenant_id: str) -> Order:
        pass

    def update_shipment_priority(self, order_id: str, priority: str, tenant_id: str) -> Order | None:
        pass

    def get_all_orders(self) -> List[Order]:
        conn = connect_db(read_only=True)
        cur = conn.cursor()
        cur.execute("""
            SELECT o.id, o.dealer_id, o.status, o.shipment_priority, o.history
            FROM orders o
        """)
        order_rows = cur.fetchall()

        orders = []
        for row in order_rows:
            order_id = row[0]
            cur.execute("""
                SELECT oi.dealer_product_id, oi.quantity
                FROM order_items oi
                WHERE oi.order_id = ?
            """, (order_id,))
            item_rows = cur.fetchall()
            items = [OrderItem(dealer_product_id=item[0], quantity=item[1]) for item in item_rows]
            
            history_str = row[4]
            history = json.loads(history_str) if history_str else []

            orders.append(Order(
                id=row[0],
                dealer_id=row[1],
                status=row[2],
                shipment_priority=row[3],
                items=items,
                history=history,
            ))
        
        conn.close()
        return orders