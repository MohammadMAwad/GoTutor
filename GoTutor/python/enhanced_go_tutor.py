#!/usr/bin/env python3
"""
Enhanced Go Tutoring System
Features: Pattern Recognition, Joseki Database, Move Analysis, Educational AI
"""

import random
import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

class GamePhase(Enum):
    OPENING = "opening"
    MIDDLE_GAME = "middle_game" 
    ENDGAME = "endgame"

@dataclass
class Move:
    x: int
    y: int
    color: str
    move_number: int
    
    def to_coords(self) -> str:
        """Convert to Go coordinates like D4"""
        if 0 <= self.x <= 18:
            letters = "ABCDEFGHJKLMNOPQRST"  # Skip I
            return f"{letters[self.x]}{self.y + 1}"
        return f"({self.x},{self.y})"

@dataclass
class Pattern:
    name: str
    description: str
    positions: List[Tuple[int, int]]  # Relative positions
    colors: List[str]  # Colors for each position
    advice: str
    difficulty: str  # beginner, intermediate, advanced

class JosekiDatabase:
    """Database of common joseki patterns"""
    
    def __init__(self):
        self.josekis = self._load_joseki_patterns()
    
    def _load_joseki_patterns(self) -> List[Dict]:
        """Load common joseki patterns"""
        return [
            {
                "name": "3-4 Point Approach",
                "moves": ["D4", "Q16", "R14", "Q14"],
                "description": "Standard approach to 3-4 point",
                "phase": "opening",
                "advice": "This creates influence while maintaining corner territory",
                "variations": ["R15", "Q15", "R17"]
            },
            {
                "name": "Diagonal Fuseki",
                "moves": ["D4", "Q16", "D16", "Q4"],
                "description": "Balanced diagonal opening",
                "phase": "opening", 
                "advice": "Creates balanced influence in all corners",
                "variations": ["R17", "D17", "C3"]
            },
            {
                "name": "Chinese Opening",
                "moves": ["D4", "Q16", "Q4", "C6"],
                "description": "Chinese fuseki setup",
                "phase": "opening",
                "advice": "Emphasizes side territory and influence",
                "variations": ["C10", "F3", "R6"]
            },
            {
                "name": "Pincer Attack",
                "moves": ["D4", "Q16", "R14", "R12"],
                "description": "Pincer against approach move",
                "phase": "opening",
                "advice": "Creates pressure on opponent's stone",
                "variations": ["R11", "R13", "Q12"]
            },
            {
                "name": "Knight's Move Enclosure",
                "moves": ["D4", "F3"],
                "description": "Secure corner territory",
                "phase": "opening",
                "advice": "Solid corner development, good for beginners",
                "variations": ["C6", "E3", "C3"]
            }
        ]
    
    def check_joseki(self, recent_moves: List[str]) -> Optional[Dict]:
        """Check if recent moves match a known joseki"""
        if len(recent_moves) < 2:
            return None
            
        # Check last 4-6 moves for joseki patterns
        for joseki in self.josekis:
            joseki_moves = joseki["moves"]
            
            # Check if recent moves match any part of this joseki
            for i in range(len(recent_moves) - len(joseki_moves) + 1):
                sequence = recent_moves[i:i + len(joseki_moves)]
                if sequence == joseki_moves[:len(sequence)]:
                    return {
                        **joseki,
                        "matched_moves": len(sequence),
                        "total_moves": len(joseki_moves),
                        "is_complete": len(sequence) == len(joseki_moves)
                    }
        return None

class PatternRecognizer:
    """Recognizes tactical and strategic patterns"""
    
    def __init__(self):
        self.tactical_patterns = self._load_tactical_patterns()
        self.strategic_patterns = self._load_strategic_patterns()
    
    def _load_tactical_patterns(self) -> List[Pattern]:
        """Load tactical patterns like ladders, nets, etc."""
        return [
            Pattern(
                name="Ladder",
                description="Sequence of atari moves",
                positions=[(0,0), (1,1), (0,2), (1,3)],
                colors=["black", "white", "black", "white"],
                advice="Check if the ladder works before playing",
                difficulty="beginner"
            ),
            Pattern(
                name="Net",
                description="Loose containment of stones",
                positions=[(0,0), (2,1), (1,2)],
                colors=["white", "black", "black"],
                advice="The net prevents escape while maintaining connection",
                difficulty="intermediate"
            ),
            Pattern(
                name="Snapback",
                description="Sacrifice to capture back",
                positions=[(0,0), (1,0), (0,1)],
                colors=["black", "white", "white"],
                advice="Look for snapback opportunities after captures",
                difficulty="intermediate"
            ),
            Pattern(
                name="Bamboo Joint",
                description="Strong connection shape",
                positions=[(0,0), (2,0), (1,1)],
                colors=["black", "black", "black"],
                advice="Bamboo joint is nearly unbreakable",
                difficulty="beginner"
            ),
            Pattern(
                name="Tiger's Mouth",
                description="Powerful capturing shape",
                positions=[(0,0), (1,0), (0,1), (2,1)],
                colors=["black", "black", "black", "black"],
                advice="Tiger's mouth threatens multiple cuts",
                difficulty="intermediate"
            )
        ]
    
    def _load_strategic_patterns(self) -> List[Pattern]:
        """Load strategic patterns like moyos, invasions, etc."""
        return [
            Pattern(
                name="Moyo Formation",
                description="Large territorial framework",
                positions=[(3,3), (6,9), (9,6)],
                colors=["black", "black", "black"],
                advice="Build moyo with loose stones, then invite invasion",
                difficulty="advanced"
            ),
            Pattern(
                name="Invasion Point",
                description="Weak point for invasion",
                positions=[(3,3), (6,3), (9,3)],
                colors=["white", "empty", "white"],
                advice="The 3-3 point is often a good invasion",
                difficulty="intermediate"
            ),
            Pattern(
                name="Extension Base",
                description="Safe development from stones",
                positions=[(0,0), (3,0)],
                colors=["black", "black"],
                advice="Two-space extension creates good base",
                difficulty="beginner"
            )
        ]
    
    def find_patterns(self, board_state: Dict, recent_move: Move) -> List[Dict]:
        """Find patterns around recent move"""
        found_patterns = []
        
        # Check tactical patterns around the recent move
        for pattern in self.tactical_patterns:
            if self._pattern_matches_near_move(board_state, recent_move, pattern):
                found_patterns.append({
                    "type": "tactical",
                    "pattern": pattern,
                    "location": recent_move.to_coords(),
                    "urgency": "high" if pattern.difficulty == "beginner" else "medium"
                })
        
        # Check strategic patterns
        for pattern in self.strategic_patterns:
            if self._strategic_pattern_present(board_state, pattern):
                found_patterns.append({
                    "type": "strategic", 
                    "pattern": pattern,
                    "urgency": "medium"
                })
        
        return found_patterns
    
    def _pattern_matches_near_move(self, board_state: Dict, move: Move, pattern: Pattern) -> bool:
        """Check if tactical pattern exists near the move"""
        # Simplified pattern matching - in reality this would be more sophisticated
        return random.random() < 0.3  # 30% chance to find a pattern
    
    def _strategic_pattern_present(self, board_state: Dict, pattern: Pattern) -> bool:
        """Check for strategic patterns"""
        return random.random() < 0.2  # 20% chance

class MoveAnalyzer:
    """Analyzes individual moves for educational content"""
    
    def __init__(self):
        self.move_types = {
            "corner": "Corner moves secure territory early",
            "side": "Side moves balance territory and influence", 
            "center": "Center moves emphasize fighting and influence",
            "approach": "Approach moves put pressure on opponent corners",
            "extension": "Extensions create stable groups",
            "invasion": "Invasions reduce opponent territory",
            "attack": "Attacking moves create pressure",
            "defense": "Defensive moves protect your groups",
            "connection": "Connection moves link your stones",
            "cut": "Cutting moves separate opponent stones"
        }
    
    def analyze_move(self, move: Move, board_state: Dict, game_phase: GamePhase) -> Dict:
        """Provide detailed analysis of a move"""
        move_type = self._classify_move(move, board_state, game_phase)
        
        analysis = {
            "coordinate": move.to_coords(),
            "type": move_type,
            "description": self.move_types.get(move_type, "Positional move"),
            "phase_appropriateness": self._rate_for_phase(move_type, game_phase),
            "territorial_value": self._estimate_territorial_value(move, game_phase),
            "influence_value": self._estimate_influence_value(move, game_phase),
            "safety_rating": self._rate_safety(move, board_state),
            "learning_points": self._generate_learning_points(move, move_type, game_phase)
        }
        
        return analysis
    
    def _classify_move(self, move: Move, board_state: Dict, phase: GamePhase) -> str:
        """Classify the type of move"""
        x, y = move.x, move.y
        
        # Corner moves (0-5 from edges)
        if (x <= 5 or x >= 13) and (y <= 5 or y >= 13):
            return "corner"
        
        # Center moves
        elif 7 <= x <= 11 and 7 <= y <= 11:
            return "center"
        
        # Side moves
        else:
            # Simplified classification based on phase and position
            if phase == GamePhase.OPENING:
                return random.choice(["approach", "extension", "corner"])
            elif phase == GamePhase.MIDDLE_GAME:
                return random.choice(["attack", "defense", "invasion", "connection"])
            else:
                return random.choice(["defense", "territorial", "endgame"])
    
    def _rate_for_phase(self, move_type: str, phase: GamePhase) -> str:
        """Rate how appropriate move type is for game phase"""
        appropriateness = {
            GamePhase.OPENING: {
                "corner": "excellent", "approach": "good", "extension": "good",
                "center": "questionable", "invasion": "premature"
            },
            GamePhase.MIDDLE_GAME: {
                "attack": "excellent", "defense": "good", "invasion": "good",
                "corner": "slow", "connection": "good"
            },
            GamePhase.ENDGAME: {
                "defense": "excellent", "territorial": "excellent",
                "attack": "risky", "center": "usually small"
            }
        }
        
        return appropriateness.get(phase, {}).get(move_type, "neutral")
    
    def _estimate_territorial_value(self, move: Move, phase: GamePhase) -> int:
        """Estimate territorial value (1-10)"""
        base_value = 5
        
        # Corner moves worth more in opening
        if phase == GamePhase.OPENING and self._is_corner_area(move):
            base_value += 2
        
        # Edge moves worth more in endgame  
        if phase == GamePhase.ENDGAME and self._is_edge_area(move):
            base_value += 3
            
        return min(10, max(1, base_value + random.randint(-2, 2)))
    
    def _estimate_influence_value(self, move: Move, phase: GamePhase) -> int:
        """Estimate influence value (1-10)"""
        base_value = 5
        
        # Center moves have more influence
        if self._is_center_area(move):
            base_value += 3
            
        # Influence more important in opening/middle game
        if phase in [GamePhase.OPENING, GamePhase.MIDDLE_GAME]:
            base_value += 1
            
        return min(10, max(1, base_value + random.randint(-2, 2)))
    
    def _rate_safety(self, move: Move, board_state: Dict) -> str:
        """Rate how safe the move is"""
        # Simplified safety rating
        safety_options = ["very safe", "safe", "neutral", "risky", "dangerous"]
        return random.choice(safety_options)
    
    def _generate_learning_points(self, move: Move, move_type: str, phase: GamePhase) -> List[str]:
        """Generate educational points about the move"""
        points = []
        
        if move_type == "corner":
            points.extend([
                "Corner moves secure territory and provide a base for development",
                "Consider the direction of your development after corner moves",
                "3-3 invasions are always possible later"
            ])
        elif move_type == "center":
            points.extend([
                "Center moves emphasize influence over territory",
                "Make sure your groups are safe before playing in center",
                "Center stones can be attacked from multiple directions"
            ])
        elif move_type == "approach":
            points.extend([
                "Approach moves put pressure on opponent corners",
                "Be prepared for pincer attacks",
                "Consider your backup plans if opponent resists"
            ])
        
        # Add phase-specific advice
        if phase == GamePhase.OPENING:
            points.append("In opening, prioritize corner development and good shape")
        elif phase == GamePhase.MIDDLE_GAME:
            points.append("In middle game, look for attacking and defending opportunities")
        else:
            points.append("In endgame, focus on territorial moves and precise calculation")
        
        return points[:3]  # Return top 3 points
    
    def _is_corner_area(self, move: Move) -> bool:
        return (move.x <= 5 or move.x >= 13) and (move.y <= 5 or move.y >= 13)
    
    def _is_center_area(self, move: Move) -> bool:
        return 7 <= move.x <= 11 and 7 <= move.y <= 11
    
    def _is_edge_area(self, move: Move) -> bool:
        return move.x <= 2 or move.x >= 16 or move.y <= 2 or move.y >= 16

class EnhancedGoTutor:
    """Enhanced tutoring system with pattern recognition and joseki"""
    
    def __init__(self):
        self.joseki_db = JosekiDatabase()
        self.pattern_recognizer = PatternRecognizer()
        self.move_analyzer = MoveAnalyzer()
        self.game_history = []
        self.move_count = 0
    
    def add_move(self, coordinate: str, color: str):
        """Add a move to the game history"""
        move = self._parse_coordinate(coordinate, color, self.move_count + 1)
        self.game_history.append(move)
        self.move_count += 1
        return move
    
    def _parse_coordinate(self, coord: str, color: str, move_num: int) -> Move:
        """Parse coordinate string like 'D4' into Move object"""
        if len(coord) >= 2:
            letter = coord[0].upper()
            number = int(coord[1:])
            
            letters = "ABCDEFGHJKLMNOPQRST"
            x = letters.index(letter) if letter in letters else 0
            y = number - 1
            
            return Move(x, y, color, move_num)
        
        return Move(3, 3, color, move_num)  # Default
    
    def analyze_current_position(self) -> Dict:
        """Comprehensive analysis of current position"""
        if not self.game_history:
            return self._opening_guidance()
        
        recent_move = self.game_history[-1]
        game_phase = self._determine_phase()
        
        # Get recent move coordinates for joseki checking
        recent_coords = [move.to_coords() for move in self.game_history[-6:]]
        
        # Perform all analyses
        joseki_info = self.joseki_db.check_joseki(recent_coords)
        board_state = self._create_board_state()
        patterns = self.pattern_recognizer.find_patterns(board_state, recent_move)
        move_analysis = self.move_analyzer.analyze_move(recent_move, board_state, game_phase)
        
        return {
            "move_number": self.move_count,
            "game_phase": game_phase,
            "recent_move": recent_move,
            "move_analysis": move_analysis,
            "joseki_info": joseki_info,
            "patterns_found": patterns,
            "tactical_advice": self._generate_tactical_advice(patterns),
            "strategic_advice": self._generate_strategic_advice(game_phase),
            "questions": self._generate_questions(game_phase, patterns, joseki_info)
        }
    
    def _determine_phase(self) -> GamePhase:
        """Determine current game phase"""
        if self.move_count < 30:
            return GamePhase.OPENING
        elif self.move_count < 120:
            return GamePhase.MIDDLE_GAME
        else:
            return GamePhase.ENDGAME
    
    def _create_board_state(self) -> Dict:
        """Create simplified board state from move history"""
        board = {}
        for move in self.game_history:
            board[(move.x, move.y)] = move.color
        return board
    
    def _opening_guidance(self) -> Dict:
        """Special guidance for game start"""
        return {
            "move_number": 0,
            "game_phase": GamePhase.OPENING,
            "advice": "Start with corner moves to secure territory",
            "questions": ["Which corner appeals to you and why?"],
            "joseki_info": None,
            "patterns_found": []
        }
    
    def _generate_tactical_advice(self, patterns: List[Dict]) -> List[str]:
        """Generate advice based on found patterns"""
        advice = []
        
        for pattern_info in patterns:
            if pattern_info["type"] == "tactical":
                pattern = pattern_info["pattern"]
                advice.append(f"🔍 {pattern.name}: {pattern.advice}")
        
        if not advice:
            advice.append("🔍 Look for tactical opportunities like cuts, connections, and captures")
        
        return advice
    
    def _generate_strategic_advice(self, phase: GamePhase) -> List[str]:
        """Generate strategic advice based on game phase"""
        advice_by_phase = {
            GamePhase.OPENING: [
                "📋 Secure corners before playing in the center",
                "📋 Balance territory and influence in your moves",
                "📋 Develop towards the center from secure bases"
            ],
            GamePhase.MIDDLE_GAME: [
                "⚔️ Look for attacks against weak groups",
                "⚔️ Ensure your own groups have good shape",
                "⚔️ Control key points and territory boundaries"
            ],
            GamePhase.ENDGAME: [
                "📏 Count territory and find the biggest moves",
                "📏 Look for sente (forcing) endgame sequences",
                "📏 Protect your territory while reducing opponent's"
            ]
        }
        
        return advice_by_phase.get(phase, ["Think about your overall strategy"])
    
    def _generate_questions(self, phase: GamePhase, patterns: List[Dict], joseki_info: Optional[Dict]) -> List[str]:
        """Generate Socratic questions"""
        questions = []
        
        # Phase-specific questions
        phase_questions = {
            GamePhase.OPENING: [
                "How does this move help your overall opening strategy?",
                "Are you balancing territory and influence effectively?",
                "What would you do if opponent approaches your corner?"
            ],
            GamePhase.MIDDLE_GAME: [
                "Which groups on the board need the most attention?",
                "How would you evaluate the current fighting?",
                "What would happen if opponent plays elsewhere?"
            ],
            GamePhase.ENDGAME: [
                "Which endgame move is worth the most points?",
                "Are there any sente sequences you should play first?",
                "How secure is your territory?"
            ]
        }
        
        questions.extend(phase_questions.get(phase, [])[:2])
        
        # Pattern-specific questions
        if patterns:
            questions.append("Do you see any tactical patterns in this area?")
        
        # Joseki-specific questions
        if joseki_info:
            questions.append(f"Why might the {joseki_info['name']} be appropriate here?")
        
        return questions
    
    def generate_tutorial_message(self, analysis: Dict) -> str:
        """Generate comprehensive tutorial message"""
        phase = analysis["game_phase"]
        move_num = analysis["move_number"]
        
        if move_num == 0:
            return self._generate_opening_message()
        
        recent_move = analysis["recent_move"]
        move_analysis = analysis["move_analysis"]
        joseki_info = analysis.get("joseki_info")
        patterns = analysis.get("patterns_found", [])
        
        message = f"""
🎓 ENHANCED TUTORING - Move {move_num}
{'='*60}

📍 Last Move: {recent_move.to_coords()} ({recent_move.color})
📊 Game Phase: {phase.value.replace('_', ' ').title()}

🔍 MOVE ANALYSIS:
• Type: {move_analysis['type'].title()} move
• Description: {move_analysis['description']}
• Phase Rating: {move_analysis['phase_appropriateness'].title()}
• Territory Value: {move_analysis['territorial_value']}/10
• Influence Value: {move_analysis['influence_value']}/10
• Safety: {move_analysis['safety_rating'].title()}

"""
        
        # Add joseki information
        if joseki_info:
            status = "Complete!" if joseki_info['is_complete'] else f"In progress ({joseki_info['matched_moves']}/{joseki_info['total_moves']})"
            message += f"""
📚 JOSEKI DETECTED:
• Pattern: {joseki_info['name']} - {status}
• {joseki_info['description']}
• Key Point: {joseki_info['advice']}
"""
            if not joseki_info['is_complete']:
                message += f"• Next moves to consider: {', '.join(joseki_info['variations'])}\n"
        
        # Add pattern information
        if patterns:
            message += f"\n🔍 PATTERNS FOUND:\n"
            for pattern_info in patterns[:2]:  # Show top 2 patterns
                pattern = pattern_info['pattern']
                message += f"• {pattern.name}: {pattern.advice}\n"
        
        # Add learning points
        if move_analysis['learning_points']:
            message += f"\n💡 KEY LEARNING POINTS:\n"
            for point in move_analysis['learning_points']:
                message += f"• {point}\n"
        
        # Add tactical advice
        tactical_advice = analysis.get('tactical_advice', [])
        if tactical_advice:
            message += f"\n{tactical_advice[0]}\n"
        
        # Add strategic advice
        strategic_advice = analysis.get('strategic_advice', [])
        if strategic_advice:
            message += f"\n{strategic_advice[0]}\n"
        
        # Add questions
        questions = analysis.get('questions', [])
        if questions:
            message += f"\n🤔 THINK ABOUT:\n"
            for question in questions[:2]:
                message += f"• {question}\n"
        
        message += f"\n🎯 Before your next move, consider the key learning points above!"
        message += f"\n{'='*60}"
        
        return message
    
    def _generate_opening_message(self) -> str:
        """Special message for game start"""
        return """
🎓 ENHANCED GO TUTORING - Game Start
====================================

🌟 Welcome to your Go learning journey!

🎯 OPENING STRATEGY:
• Corner moves (3-3, 3-4, 4-4) secure territory
• Consider both territory and influence
• Traditional opening: corners → sides → center

🤔 THINK ABOUT:
• Which corner feels right to y