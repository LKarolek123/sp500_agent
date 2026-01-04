"""
XTB API Connector

Low-level WebSocket/TCP connection to XTB xAPI.
Handles authentication, streaming data, and trade execution.

Docs: http://developers.xtb.com/documentation/
"""
import json
import socket
import time
from typing import Dict, Optional, Any
from datetime import datetime


class XTBConnector:
    """XTB xAPI connection handler."""
    
    # Server endpoints
    DEMO_SERVER = "xapi.xtb.com"
    DEMO_PORT = 5124
    DEMO_STREAM_PORT = 5125
    
    REAL_SERVER = "xapi.xtb.com"
    REAL_PORT = 5112
    REAL_STREAM_PORT = 5113
    
    def __init__(self, user_id: str, password: str, mode: str = "demo"):
        """
        Initialize XTB connector.
        
        Args:
            user_id: XTB account login
            password: XTB account password
            mode: 'demo' or 'real'
        """
        self.user_id = user_id
        self.password = password
        self.mode = mode
        
        # Connection state
        self.socket = None
        self.stream_socket = None
        self.session_id = None
        self.connected = False
        
        # Set server based on mode
        if mode == "demo":
            self.server = self.DEMO_SERVER
            self.port = self.DEMO_PORT
            self.stream_port = self.DEMO_STREAM_PORT
        else:
            self.server = self.REAL_SERVER
            self.port = self.REAL_PORT
            self.stream_port = self.REAL_STREAM_PORT
    
    def connect(self) -> bool:
        """
        Connect to XTB API and authenticate.
        
        Returns:
            True if connection successful
        """
        try:
            print(f"Connecting to XTB {self.mode.upper()} server...")
            print(f"  Server: {self.server}:{self.port}")
            
            # Create TCP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server, self.port))
            
            # Login command
            login_cmd = {
                "command": "login",
                "arguments": {
                    "userId": self.user_id,
                    "password": self.password
                }
            }
            
            response = self._send_command(login_cmd)
            
            if response.get("status"):
                self.session_id = response.get("streamSessionId")
                self.connected = True
                print("✓ Connected successfully")
                print(f"  Session ID: {self.session_id}")
                return True
            else:
                error = response.get("errorDescr", "Unknown error")
                print(f"✗ Login failed: {error}")
                return False
                
        except Exception as e:
            print(f"✗ Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from API."""
        if self.connected:
            try:
                self._send_command({"command": "logout"})
            except:
                pass
            
        if self.socket:
            self.socket.close()
            self.socket = None
            
        if self.stream_socket:
            self.stream_socket.close()
            self.stream_socket = None
            
        self.connected = False
        print("Disconnected from XTB")
    
    def _send_command(self, command: Dict) -> Dict:
        """
        Send command to API and get response.
        
        Args:
            command: Command dictionary
            
        Returns:
            Response dictionary
        """
        if not self.socket:
            raise ConnectionError("Not connected to API")
        
        # Send command
        cmd_json = json.dumps(command) + "\n\n"
        self.socket.sendall(cmd_json.encode('utf-8'))
        
        # Receive response
        response = b""
        while True:
            chunk = self.socket.recv(4096)
            response += chunk
            if b"\n\n" in response:
                break
        
        # Parse JSON
        try:
            return json.loads(response.decode('utf-8').strip())
        except json.JSONDecodeError as e:
            print(f"Failed to parse response: {response}")
            raise e
    
    def get_account_info(self) -> Optional[Dict]:
        """Get account balance and margin info."""
        try:
            response = self._send_command({"command": "getMarginLevel"})
            if response.get("status"):
                data = response.get("returnData", {})
                return {
                    "balance": data.get("balance"),
                    "equity": data.get("equity"),
                    "margin": data.get("margin"),
                    "margin_free": data.get("margin_free"),
                    "margin_level": data.get("margin_level"),
                    "currency": data.get("currency")
                }
        except Exception as e:
            print(f"Error getting account info: {e}")
        return None
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        Get symbol information (bid, ask, spread, etc.).
        
        Args:
            symbol: Trading symbol (e.g., 'US500')
        """
        try:
            cmd = {
                "command": "getSymbol",
                "arguments": {
                    "symbol": symbol
                }
            }
            response = self._send_command(cmd)
            
            if response.get("status"):
                return response.get("returnData")
        except Exception as e:
            print(f"Error getting symbol info: {e}")
        return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current bid price for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Current bid price or None
        """
        info = self.get_symbol_info(symbol)
        if info:
            return info.get("bid")
        return None
    
    def get_open_trades(self) -> list:
        """Get list of currently open trades."""
        try:
            cmd = {
                "command": "getTrades",
                "arguments": {
                    "openedOnly": True
                }
            }
            response = self._send_command(cmd)
            
            if response.get("status"):
                return response.get("returnData", [])
        except Exception as e:
            print(f"Error getting open trades: {e}")
        return []
    
    def open_trade(self, 
                   symbol: str,
                   cmd_type: int,  # 0=BUY, 1=SELL
                   volume: float,
                   sl: Optional[float] = None,
                   tp: Optional[float] = None,
                   comment: str = "") -> Optional[int]:
        """
        Open a new trade.
        
        Args:
            symbol: Trading symbol (e.g., 'US500')
            cmd_type: 0 for BUY, 1 for SELL
            volume: Volume in lots
            sl: Stop loss price (optional)
            tp: Take profit price (optional)
            comment: Trade comment
            
        Returns:
            Order ID if successful, None otherwise
        """
        try:
            trade_trans = {
                "command": "tradeTransaction",
                "arguments": {
                    "tradeTransInfo": {
                        "cmd": cmd_type,
                        "symbol": symbol,
                        "volume": volume,
                        "type": 0,  # OPEN
                        "price": 1,  # Market order
                        "sl": sl or 0,
                        "tp": tp or 0,
                        "customComment": comment,
                        "expiration": 0
                    }
                }
            }
            
            response = self._send_command(trade_trans)
            
            if response.get("status"):
                order_id = response.get("returnData", {}).get("order")
                print(f"✓ Trade opened: Order #{order_id}")
                return order_id
            else:
                error = response.get("errorDescr", "Unknown error")
                print(f"✗ Trade failed: {error}")
                return None
                
        except Exception as e:
            print(f"Error opening trade: {e}")
            return None
    
    def close_trade(self, order_id: int, volume: float) -> bool:
        """
        Close an existing trade.
        
        Args:
            order_id: Order ID to close
            volume: Volume to close
            
        Returns:
            True if successful
        """
        try:
            # Get trade details first
            trades = self.get_open_trades()
            trade = next((t for t in trades if t["order"] == order_id), None)
            
            if not trade:
                print(f"Trade {order_id} not found")
                return False
            
            # Close command (opposite direction)
            close_cmd = 1 if trade["cmd"] == 0 else 0
            
            trade_trans = {
                "command": "tradeTransaction",
                "arguments": {
                    "tradeTransInfo": {
                        "cmd": close_cmd,
                        "symbol": trade["symbol"],
                        "volume": volume,
                        "type": 2,  # CLOSE
                        "order": order_id,
                        "price": 1  # Market
                    }
                }
            }
            
            response = self._send_command(trade_trans)
            
            if response.get("status"):
                print(f"✓ Trade closed: Order #{order_id}")
                return True
            else:
                error = response.get("errorDescr", "Unknown error")
                print(f"✗ Close failed: {error}")
                return False
                
        except Exception as e:
            print(f"Error closing trade: {e}")
            return False
    
    def modify_trade(self, 
                     order_id: int,
                     sl: Optional[float] = None,
                     tp: Optional[float] = None) -> bool:
        """
        Modify SL/TP on existing trade.
        
        Args:
            order_id: Order to modify
            sl: New stop loss (optional)
            tp: New take profit (optional)
            
        Returns:
            True if successful
        """
        try:
            trades = self.get_open_trades()
            trade = next((t for t in trades if t["order"] == order_id), None)
            
            if not trade:
                print(f"Trade {order_id} not found")
                return False
            
            trade_trans = {
                "command": "tradeTransaction",
                "arguments": {
                    "tradeTransInfo": {
                        "cmd": trade["cmd"],
                        "symbol": trade["symbol"],
                        "volume": trade["volume"],
                        "type": 3,  # MODIFY
                        "order": order_id,
                        "sl": sl or trade.get("sl", 0),
                        "tp": tp or trade.get("tp", 0),
                        "price": 1
                    }
                }
            }
            
            response = self._send_command(trade_trans)
            
            if response.get("status"):
                print(f"✓ Trade modified: Order #{order_id}")
                return True
            else:
                error = response.get("errorDescr", "Unknown error")
                print(f"✗ Modify failed: {error}")
                return False
                
        except Exception as e:
            print(f"Error modifying trade: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# Quick test
if __name__ == "__main__":
    print("XTB Connector Test")
    print("=" * 50)
    
    # Load credentials from config
    import json
    from pathlib import Path
    
    config_path = Path(__file__).parent.parent.parent / "config" / "xtb_config.json"
    
    try:
        with open(config_path) as f:
            config = json.load(f)
            demo_config = config.get("xtb_demo", {})
            USER_ID = demo_config.get("user_id", "")
            PASSWORD = demo_config.get("password", "")
    except Exception as e:
        print(f"Error loading config: {e}")
        USER_ID = ""
        PASSWORD = ""
    
    if not USER_ID or USER_ID == "your_demo_login":
        print("\n⚠️  Please edit config/xtb_config.json and add your XTB demo credentials")
        print("   Get them from: https://www.xtb.com/pl/demo")
        exit(1)
    
    # Test connection
    with XTBConnector(USER_ID, PASSWORD, mode="demo") as xtb:
        if xtb.connected:
            print("\n📊 Account Info:")
            acc_info = xtb.get_account_info()
            if acc_info:
                for key, value in acc_info.items():
                    print(f"  {key}: {value}")
            
            print("\n📈 US500 Info:")
            symbol_info = xtb.get_symbol_info("US500")
            if symbol_info:
                print(f"  Bid: {symbol_info.get('bid')}")
                print(f"  Ask: {symbol_info.get('ask')}")
                print(f"  Spread: {symbol_info.get('spreadRaw')}")
            
            print("\n📋 Open Trades:")
            trades = xtb.get_open_trades()
            if trades:
                for t in trades:
                    print(f"  Order #{t['order']}: {t['symbol']} {t['cmd']} {t['volume']} lots")
            else:
                print("  No open trades")
