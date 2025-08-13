import unittest
import os
import sys
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app
from services import TradingService, StrategyService

class TestStateMachineLogic(unittest.TestCase):
    """
    Test the logical integrity of the trade state machine.
    Ensures that operations cannot be performed on trades in invalid states (e.g., soft-deleted).
    """

    def setUp(self):
        """Set up a test client and initialize a trade for testing."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # Services
        self.strategy_service = StrategyService()
        self.trading_service = TradingService()

        # Initial data
        self.strategy_service.create_strategy(name="State Machine Test Strategy", description="Test")
        strategies = self.strategy_service.get_all_strategies()
        self.strategy = next(s for s in strategies if s['name'] == "State Machine Test Strategy")
        
        # Create a trade and close it
        _, self.trade_id = self.trading_service.add_buy_transaction(
            strategy=self.strategy['id'],
            symbol_code="STATETEST",
            symbol_name="State Test Inc.",
            price=Decimal("100.00"),
            quantity=100,
            transaction_date='2025-01-01'
        )
        self.trading_service.add_sell_transaction(
            trade_id=self.trade_id,
            price=Decimal("110.00"),
            quantity=100,
            transaction_date='2025-01-02'
        )

    def tearDown(self):
        """Clean up after tests."""
        self.app_context.pop()

    def test_cannot_add_sell_to_deleted_trade(self):
        """Verify that a sell transaction cannot be added to a soft-deleted trade."""
        # Soft-delete the trade first
        delete_success = self.trading_service.soft_delete_trade(
            trade_id=self.trade_id,
            confirmation_code="CONFIRM",
            delete_reason="Testing state machine"
        )
        self.assertTrue(delete_success, "Failed to soft-delete the trade for setup.")

        # Attempt to add a sell transaction to the now-deleted trade
        success, message = self.trading_service.add_sell_transaction(
            trade_id=self.trade_id,
            price=Decimal("120.00"),
            quantity=1,
            transaction_date='2025-01-03'
        )

        self.assertFalse(success, "Should not be able to add a sell transaction to a deleted trade.")
        self.assertIn("该交易已被删除，无法操作", message, "Incorrect error message for selling to a deleted trade.")

    def test_cannot_edit_deleted_trade(self):
        """Verify that a soft-deleted trade cannot be edited."""
        # Soft-delete the trade
        self.trading_service.soft_delete_trade(
            trade_id=self.trade_id,
            confirmation_code="CONFIRM",
            delete_reason="Testing state machine"
        )

        # Attempt to edit the deleted trade
        success, message = self.trading_service.edit_trade(
            trade_id=self.trade_id,
            updates={'symbol_name': "DeletedCo"},
            modification_reason="Attempting to edit a deleted trade"
        )

        self.assertFalse(success, "Should not be able to edit a deleted trade.")
        self.assertIn("该交易已被删除，无法编辑", message, "Incorrect error message for editing a deleted trade.")

    def test_cannot_update_details_of_deleted_trade(self):
        """Verify that details of a soft-deleted trade cannot be updated."""
        # Get a detail_id for later use
        details = self.trading_service.get_trade_details(self.trade_id)
        self.assertGreater(len(details), 0, "Trade should have details to update.")
        detail_id_to_update = details[0]['id']

        # Soft-delete the trade
        self.trading_service.soft_delete_trade(
            trade_id=self.trade_id,
            confirmation_code="CONFIRM",
            delete_reason="Testing state machine"
        )

        # Attempt to update details of the deleted trade
        detail_updates = [{
            'detail_id': detail_id_to_update,
            'price': Decimal("999.99")
        }]
        success, message = self.trading_service.update_trade_record(
            trade_id=self.trade_id,
            detail_updates=detail_updates
        )

        self.assertFalse(success, "Should not be able to update details of a deleted trade.")
        self.assertIn("不存在或已被删除", message, "Incorrect error message for updating details of a deleted trade.")

if __name__ == '__main__':
    unittest.main()
