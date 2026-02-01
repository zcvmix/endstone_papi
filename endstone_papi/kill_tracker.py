from __future__ import annotations

import time
from typing import Dict, Optional
from endstone import Player


class KillTracker:
    """Tracks player kills and killstreaks with combat timer."""
    
    def __init__(self, combat_timeout: float = 10.0):
        """
        Initialize the kill tracker.
        
        Args:
            combat_timeout: Time in seconds after which damage becomes invalid for kill credit (default: 10 seconds)
        """
        # Dictionary to store kill counts: {player_name: kill_count}
        self._kills: Dict[str, int] = {}
        # Dictionary to store current killstreaks: {player_name: streak_count}
        self._killstreaks: Dict[str, int] = {}
        # Dictionary to track last damage dealt: {victim_name: (damager_name, timestamp)}
        self._last_damage: Dict[str, tuple[str, float]] = {}
        # Combat timeout in seconds
        self._combat_timeout = combat_timeout
    
    def record_damage(self, victim: Player, damager: Player) -> None:
        """
        Record damage dealt by a player to another player.
        
        Args:
            victim: The player who took damage
            damager: The player who dealt the damage
        """
        victim_name = victim.name
        damager_name = damager.name
        current_time = time.time()
        
        # Record the damage with timestamp
        self._last_damage[victim_name] = (damager_name, current_time)
    
    def get_valid_killer(self, victim: Player) -> Optional[str]:
        """
        Get the name of the player who should receive kill credit, if any.
        Returns None if the last damage is too old or doesn't exist.
        
        Args:
            victim: The player who died
            
        Returns:
            The name of the killer if damage is recent enough, None otherwise
        """
        victim_name = victim.name
        
        if victim_name not in self._last_damage:
            return None
        
        damager_name, damage_time = self._last_damage[victim_name]
        current_time = time.time()
        time_elapsed = current_time - damage_time
        
        # Check if the damage is still valid (within timeout)
        if time_elapsed <= self._combat_timeout:
            return damager_name
        
        return None
    
    def add_kill(self, player: Player) -> None:
        """
        Add a kill to the player's count and increment their killstreak.
        
        Args:
            player: The player who got the kill
        """
        player_name = player.name
        
        # Increment total kills
        self._kills[player_name] = self._kills.get(player_name, 0) + 1
        
        # Increment killstreak
        self._killstreaks[player_name] = self._killstreaks.get(player_name, 0) + 1
    
    def reset_killstreak(self, player: Player) -> None:
        """
        Reset a player's killstreak (called when they die).
        
        Args:
            player: The player whose killstreak should be reset
        """
        player_name = player.name
        self._killstreaks[player_name] = 0
        
        # Clean up the damage record for this player
        self._last_damage.pop(player_name, None)
    
    def get_kills(self, player: Player) -> int:
        """
        Get the total kill count for a player.
        
        Args:
            player: The player to get kills for
            
        Returns:
            The player's total kill count
        """
        return self._kills.get(player.name, 0)
    
    def get_killstreak(self, player: Player) -> int:
        """
        Get the current killstreak for a player.
        
        Args:
            player: The player to get killstreak for
            
        Returns:
            The player's current killstreak
        """
        return self._killstreaks.get(player.name, 0)
    
    def clear_player_data(self, player_name: str) -> None:
        """
        Clear all data for a player (useful when they leave).
        
        Args:
            player_name: The name of the player to clear data for
        """
        self._kills.pop(player_name, None)
        self._killstreaks.pop(player_name, None)
        self._last_damage.pop(player_name, None)
    
    def cleanup_old_damage_records(self) -> None:
        """
        Clean up damage records that are older than the combat timeout.
        This can be called periodically to free up memory.
        """
        current_time = time.time()
        expired_victims = [
            victim_name
            for victim_name, (_, damage_time) in self._last_damage.items()
            if current_time - damage_time > self._combat_timeout
        ]
        
        for victim_name in expired_victims:
            del self._last_damage[victim_name]