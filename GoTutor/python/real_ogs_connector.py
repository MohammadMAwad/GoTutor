#!/usr/bin/env python3
"""
Real OGS Game Connector
Connects to actual live OGS games and monitors them
"""

import asyncio
import websockets
import json
import requests
import time
import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Import our enhanced tutor
try:
    from enhanced_go_tutor import EnhancedGoTutor
except ImportError:
    print("Warning: enhanced_go_tutor.py not found. Some features may not work.")
    EnhancedGoTutor = None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OGSGameState:
    """Represents the state of an OGS game"""
    
    def __init__(self):
        self.game_id = None
        self.players = {}
        self.moves = []
        self.current_phase = "play"
        self.board_size = 19
        self.move_count = 0

@dataclass
class OGSGameInfo:
    game_id: str
    players: Dict[str, str]  # color -> player name
    current_phase: str
    board_size: int
    time_control: Dict
    move_count: int
    current_player: str

class RealOGSConnector:
    """Enhanced OGS connector that actually works with live games"""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.websocket = None
        self.is_authenticated = False
        self.user_id = None
        self.auth_token = None
        
    async def authenticate(self) -> bool:
        """Authenticate with OGS using multiple methods"""
        logger.info("🔐 Authenticating with OGS...")
        
        try:
            # Method 1: Try to get current user info (if already logged in browser)
            response = self.session.get("https://online-go.com/api/v1/me", timeout=10)
            if response.status_code == 200:
                user_data = response.json()
                self.user_id = user_data.get("id")
                logger.info(f"✅ Already authenticated! User ID: {self.user_id}")
                self.is_authenticated = True
                return True
                
        except Exception as e:
            logger.debug(f"Not already authenticated: {e}")
        
        # Method 2: API-based login
        try:
            login_endpoints = [
                "https://online-go.com/api/v1/login",
                "https://online-go.com/api/v0/login"
            ]
            
            for endpoint in login_endpoints:
                try:
                    login_data = {
                        "username": self.username,
                        "password": self.password
                    }
                    
                    response = self.session.post(endpoint, json=login_data, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.auth_token = data.get("jwt") or data.get("token")
                        self.user_id = data.get("id")
                        
                        if self.auth_token and self.user_id:
                            logger.info(f"✅ API login successful! User ID: {self.user_id}")
                            self.is_authenticated = True
                            return True
                    
                except Exception as e:
                    logger.debug(f"API endpoint {endpoint} failed: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"API login failed: {e}")
        
        # Method 3: Session-based login
        try:
            logger.info("🔄 Trying session-based login...")
            
            # Get login page
            login_page = self.session.get("https://online-go.com/sign-in")
            
            # Prepare login data
            login_data = {
                "username": self.username,
                "password": self.password
            }
            
            # Try form-based login
            response = self.session.post(
                "https://online-go.com/sign-in", 
                data=login_data,
                allow_redirects=True
            )
            
            # Check if login was successful
            if "dashboard" in response.url or response.status_code == 200:
                # Try to get user info again
                user_response = self.session.get("https://online-go.com/api/v1/me")
                if user_response.status_code == 200:
                    user_data = user_response.json()
                    self.user_id = user_data.get("id")
                    logger.info(f"✅ Session login successful! User ID: {self.user_id}")
                    self.is_authenticated = True
                    return True
            
        except Exception as e:
            logger.error(f"Session login failed: {e}")
        
        logger.error("❌ Could not authenticate with OGS")
        logger.info("💡 Make sure you're logged into OGS in your browser first")
        return False
    
    async def get_live_games(self) -> List[Dict]:
        """Get live games that we can monitor"""
        logger.info("🎮 Finding live games to monitor...")
        
        try:
            # Get games for the authenticated user
            if self.user_id:
                response = self.session.get(f"https://online-go.com/api/v1/players/{self.user_id}/games")
                if response.status_code == 200:
                    data = response.json()
                    games = data.get("results", [])
                    
                    # Filter for active games
                    live_games = [
                        game for game in games 
                        if game.get("phase") in ["play", "stone_removal"]
                    ]
                    
                    logger.info(f"✅ Found {len(live_games)} live games")
                    return live_games
            
            # Alternative: Get recent public games
            response = self.session.get("https://online-go.com/api/v1/games?page_size=20")
            if response.status_code == 200:
                data = response.json()
                games = data.get("results", [])
                
                # Filter for active games
                live_games = [
                    game for game in games 
                    if game.get("phase") in ["play"]
                ]
                
                logger.info(f"✅ Found {len(live_games)} public live games")
                return live_games[:5]  # Limit to 5 for demo
                
        except Exception as e:
            logger.error(f"Error getting live games: {e}")
        
        return []
    
    async def connect_to_websocket(self) -> bool:
        """Connect to OGS websocket for real-time updates"""
        logger.info("🔌 Connecting to OGS websocket...")
        
        try:
            # Socket.io endpoint
            ws_url = "wss://online-go.com/socket.io/?EIO=4&transport=websocket"
            
            self.websocket = await websockets.connect(
                ws_url,
                extra_headers={
                    "Origin": "https://online-go.com",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            
            logger.info("✅ Websocket connected!")
            
            # Handle initial Socket.io handshake
            welcome_msg = await self.websocket.recv()
            logger.info(f"🤝 Received: {welcome_msg[:50]}...")
            
            # Send connection acknowledgment
            if welcome_msg.startswith("0"):
                await self.websocket.send("40")
                logger.info("📡 Sent connection acknowledgment")
            
            return True
            
        except Exception as e:
            logger.error(f"Websocket connection failed: {e}")
            return False
    
    async def monitor_game(self, game_id: str, callback):
        """Monitor a specific game for moves"""
        logger.info(f"👀 Monitoring game {game_id} for moves...")
        
        if not self.websocket:
            logger.error("No websocket connection")
            return
        
        try:
            # Subscribe to game updates
            game_connect_msg = f'42["game/connect",{{"game_id":{game_id}}}]'
            await self.websocket.send(game_connect_msg)
            logger.info(f"📡 Subscribed to game {game_id}")
            
            # Listen for messages
            message_count = 0
            async for message in self.websocket:
                message_count += 1
                
                try:
                    # Parse Socket.io message
                    if message.startswith("42"):
                        # Socket.io data message
                        json_part = message[2:]  # Remove "42" prefix
                        data = json.loads(json_part)
                        
                        if isinstance(data, list) and len(data) >= 2:
                            event_type = data[0]
                            event_data = data[1] if len(data) > 1 else {}
                            
                            logger.info(f"📨 Event: {event_type}")
                            
                            # Handle different event types
                            if event_type in ["game/move", "game/gamedata"]:
                                logger.info(f"🎯 Game update detected!")
                                await callback(event_data, event_type)
                            
                    elif message.startswith("2"):
                        # Ping - respond with pong
                        await self.websocket.send("3")
                    
                    # Limit messages for demo
                    if message_count > 100:
                        logger.info("📊 Received 100+ messages, stopping monitoring")
                        break
                        
                except json.JSONDecodeError:
                    # Non-JSON message
                    logger.debug(f"Non-JSON message: {message[:50]}...")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                
        except websockets.exceptions.ConnectionClosed:
            logger.error("Websocket connection closed")
        except Exception as e:
            logger.error(f"Error monitoring game: {e}")

class OGSGameParser:
    """Parses OGS game data into our tutor format"""
    
    @staticmethod
    def parse_game_state(game_data: Dict) -> Optional[Dict]:
        """Parse OGS game data into standardized format"""
        try:
            # Extract basic game info
            game_info = {
                "game_id": str(game_data.get("id", "unknown")),
                "board_size": game_data.get("width", 19),
                "move_count": len(game_data.get("moves", [])),
                "current_phase": game_data.get("phase", "playing"),
                "players": OGSGameParser._extract_players(game_data),
                "time_control": game_data.get("time_control", {}),
                "moves": OGSGameParser._parse_moves(game_data.get("moves", []))
            }
            
            return game_info
            
        except Exception as e:
            logger.error(f"Error parsing game state: {e}")
            return None
    
    @staticmethod
    def _extract_players(game_data: Dict) -> Dict[str, str]:
        """Extract player information"""
        players = {}
        
        # Try different formats for player data
        if "players" in game_data:
            player_data = game_data["players"]
            
            if isinstance(player_data, dict):
                # Format: {"black": {"username": "..."}, "white": {...}}
                for color in ["black", "white"]:
                    if color in player_data:
                        player_info = player_data[color]
                        if isinstance(player_info, dict):
                            players[color] = player_info.get("username", f"Player {color}")
                        else:
                            players[color] = str(player_info)
            
            elif isinstance(player_data, list):
                # Format: [{"color": "black", "username": "..."}, ...]
                for player in player_data:
                    if isinstance(player, dict):
                        color = player.get("color") or player.get("colour")
                        username = player.get("username") or player.get("name")
                        if color and username:
                            players[color] = username
        
        # Fallback
        if not players:
            players = {"black": "Black Player", "white": "White Player"}
        
        return players
    
    @staticmethod
    def _parse_moves(moves_data: List) -> List[Dict]:
        """Parse move list into standardized format"""
        parsed_moves = []
        
        for i, move_data in enumerate(moves_data):
            try:
                if isinstance(move_data, list) and len(move_data) >= 2:
                    # Format: [x, y] or [x, y, color]
                    x, y = move_data[0], move_data[1]
                    color = "black" if i % 2 == 0 else "white"
                    
                elif isinstance(move_data, dict):
                    # Format: {"x": x, "y": y, "color": color}
                    x = move_data.get("x", -1)
                    y = move_data.get("y", -1)
                    color = move_data.get("color", "black" if i % 2 == 0 else "white")
                
                else:
                    continue
                
                # Convert to coordinate string
                if 0 <= x <= 18 and 0 <= y <= 18:
                    letters = "ABCDEFGHJKLMNOPQRST"
                    coord = f"{letters[x]}{y + 1}"
                    
                    parsed_moves.append({
                        "coordinate": coord,
                        "color": color,
                        "move_number": i + 1,
                        "x": x,
                        "y": y
                    })
            
            except Exception as e:
                logger.warning(f"Could not parse move {i}: {e}")
                continue
        
        return parsed_moves

class LiveOGSTutor:
    """Main class that combines OGS connection with AI tutoring"""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.ogs_connector = RealOGSConnector(username, password)
        self.ai_tutor = EnhancedGoTutor() if EnhancedGoTutor else None
        self.current_game_id = None
        self.last_move_count = 0
        self.tutoring_interval = 5  # Tutor every N moves
        
    async def start_tutoring_session(self):
        """Start the live tutoring session"""
        logger.info("🚀 Starting Live OGS AI Tutoring Session")
        logger.info("="*60)
        
        # Step 1: Authenticate
        if not await self.ogs_connector.authenticate():
            logger.error("Could not authenticate with OGS")
            return False
        
        # Step 2: Connect to websocket
        if not await self.ogs_connector.connect_to_websocket():
            logger.error("Could not connect to OGS websocket")
            return False
        
        # Step 3: Get active games
        active_games = await self.ogs_connector.get_live_games()
        
        if active_games:
            # Let user choose a game
            game_id = await self._select_game(active_games)
        else:
            # Manual game ID entry
            game_id = await self._manual_game_entry()
        
        if not game_id:
            logger.error("No game selected")
            return False
        
        self.current_game_id = game_id
        logger.info(f"🎯 Selected game: {game_id}")
        
        # Step 4: Start monitoring
        await self.ogs_connector.monitor_game(game_id, self._handle_game_update)
        
        return True
    
    async def _select_game(self, games: List[Dict]) -> Optional[str]:
        """Let user select from active games"""
        logger.info("\n🎮 Active Games Found:")
        logger.info("-" * 40)
        
        for i, game in enumerate(games[:5], 1):  # Show max 5 games
            game_id = game.get("id", "unknown")
            players = game.get("players", {})
            
            # Extract player names
            player_names = []
            if isinstance(players, dict):
                for color, player_info in players.items():
                    if isinstance(player_info, dict):
                        name = player_info.get("username", f"Player {color}")
                    else:
                        name = str(player_info)
                    player_names.append(f"{color}: {name}")
            
            logger.info(f"{i}. Game {game_id}")
            if player_names:
                logger.info(f"   Players: {', '.join(player_names)}")
            logger.info(f"   Phase: {game.get('phase', 'unknown')}")
        
        # For demo, auto-select first game
        if games:
            selected_game = games[0]
            game_id = str(selected_game.get("id", "unknown"))
            logger.info(f"🎯 Auto-selecting game: {game_id}")
            return game_id
        
        return None
    
    async def _manual_game_entry(self) -> Optional[str]:
        """Manual game ID entry"""
        logger.info("\n📝 No active games found via API.")
        logger.info("You can still monitor a specific game by ID.")
        logger.info("Example: Go to a game on OGS website and copy the ID from URL")
        logger.info("URL format: https://online-go.com/game/12345678")
        
        # For demo purposes, return None
        # In real use, you'd get user input here
        logger.info("💡 To manually enter game ID, modify this function")
        return None
    
    async def _handle_game_update(self, game_data: Dict, event_type: str):
        """Handle incoming game updates from OGS"""
        try:
            logger.info(f"\n📡 Received {event_type} event")
            
            # Parse the game state
            game_state = OGSGameParser.parse_game_state(game_data)
            
            if not game_state:
                logger.error("Could not parse game state")
                return
            
            moves = game_state.get("moves", [])
            current_move_count = len(moves)
            
            logger.info(f"📊 Game state: {current_move_count} moves")
            
            # Check if we should provide tutoring
            if self._should_provide_tutoring(current_move_count):
                await self._provide_tutoring(moves, game_state)
            
            self.last_move_count = current_move_count
            
        except Exception as e:
            logger.error(f"Error handling game update: {e}")
    
    def _should_provide_tutoring(self, current_move_count: int) -> bool:
        """Determine if we should provide tutoring now"""
        # Tutor every N moves
        move_difference = current_move_count - self.last_move_count
        
        if move_difference >= self.tutoring_interval:
            return True
        
        # Also tutor on first few moves
        if current_move_count <= 5:
            return True
        
        return False
    
    async def _provide_tutoring(self, moves: List[Dict], game_state: Dict):
        """Provide AI tutoring based on current game state"""
        logger.info(f"\n🎓 Providing AI Tutoring...")
        logger.info("="*50)
        
        try:
            if not self.ai_tutor:
                logger.warning("AI Tutor not available - enhanced_go_tutor.py not imported")
                return
            
            # Reset tutor and add all moves
            self.ai_tutor = EnhancedGoTutor()
            
            for move in moves:
                coord = move.get("coordinate", "D4")
                color = move.get("color", "black")
                self.ai_tutor.add_move(coord, color)
            
            # Get comprehensive analysis
            analysis = self.ai_tutor.analyze_current_position()
            
            # Generate tutorial message
            tutorial_message = self.ai_tutor.generate_tutorial_message(analysis)
            
            # Display tutorial
            print(tutorial_message)
            
            # Add game-specific context
            players = game_state.get("players", {})
            logger.info(f"\n🎮 Game Context:")
            logger.info(f"   Game ID: {game_state.get('game_id', 'unknown')}")
            logger.info(f"   Players: {players}")
            logger.info(f"   Board Size: {game_state.get('board_size', 19)}x{game_state.get('board_size', 19)}")
            logger.info(f"   Total Moves: {len(moves)}")
            
            logger.info("\n" + "="*50)
            
        except Exception as e:
            logger.error(f"Error providing tutoring: {e}")
    
    def set_tutoring_interval(self, interval: int):
        """Set how often to provide tutoring (every N moves)"""
        self.tutoring_interval = interval
        logger.info(f"🔄 Tutoring interval set to every {interval} moves")

# Standalone functions for easier testing
async def test_ogs_connection(username: str, password: str):
    """Test OGS connection without full tutoring"""
    connector = RealOGSConnector(username, password)
    
    logger.info("Testing OGS connection...")
    
    # Test authentication
    if await connector.authenticate():
        logger.info("✅ Authentication successful")
        
        # Test getting games
        games = await connector.get_live_games()
        logger.info(f"✅ Found {len(games)} games")
        
        # Test websocket connection
        if await connector.connect_to_websocket():
            logger.info("✅ Websocket connection successful")
            return True
    
    return False

async def monitor_specific_game(username: str, password: str, game_id: str):
    """Monitor a specific game by ID"""
    tutor = LiveOGSTutor(username, password)
    
    # Set the game ID directly
    tutor.current_game_id = game_id
    
    # Authenticate and connect
    if await tutor.ogs_connector.authenticate():
        if await tutor.ogs_connector.connect_to_websocket():
            logger.info(f"🎯 Monitoring game {game_id}")
            await tutor.ogs_connector.monitor_game(game_id, tutor._handle_game_update)

# Demo and testing functions
async def demo_live_tutor(username: str = "Mohammad Awad", password: str = "90451762"):
    """Demo the live OGS tutor"""
    logger.info("🎯 Live OGS AI Tutor Demo")
    logger.info("="*40)
    
    # Create tutor
    tutor = LiveOGSTutor(username, password)
    
    # Set tutoring frequency
    tutor.set_tutoring_interval(3)  # Tutor every 3 moves
    
    # Start tutoring session
    success = await tutor.start_tutoring_session()
    
    if success:
        logger.info("🎉 Live tutoring session started successfully!")
        logger.info("The tutor will now monitor your OGS games and provide real-time advice.")
    else:
        logger.error("❌ Could not start live tutoring session")

# Main execution
async def main():
    """Main function to run the live OGS tutor"""
    import sys
    
    logger.info("🎯 Real OGS Connector")
    logger.info("="*50)
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            # Test mode
            await test_ogs_connection("Mohammad Awad", "90451762")
        elif sys.argv[1] == "demo":
            # Demo mode
            await demo_live_tutor()
        elif sys.argv[1] == "monitor" and len(sys.argv) > 2:
            # Monitor specific game
            game_id = sys.argv[2]
            await monitor_specific_game("Mohammad Awad", "90451762", game_id)
        else:
            print("Usage: python real_ogs_connector.py [test|demo|monitor <game_id>]")
    else:
        # Default: run demo
        await demo_live_tutor()

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())