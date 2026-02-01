from endstone import Player
from endstone.command import Command, CommandSender
from endstone.event import event_handler, PlayerDeathEvent, EntityDamageByEntityEvent
from endstone.plugin import Plugin, ServicePriority

from .papi import PlaceholderAPI
from .kill_tracker import KillTracker


class PlaceholderAPIPlugin(Plugin):
    api_version = "0.6"

    commands = {
        "papi": {
            "description": "PlaceholderAPI command",
            "usages": [
                "/papi parse <player: player> <text: message>",
                "/papi list",
            ],
            "permissions": ["papi.command.papi"],
        }
    }

    permissions = {
        "papi.command.papi": {
            "description": "Allows users to use the /papi command",
            "default": "op",
        }
    }

    def __init__(self):
        super().__init__()
        self._api = PlaceholderAPI(self)
        # Initialize kill tracker with 10 second combat timeout
        # You can change this value to adjust how long damage is valid for kill credit
        self._kill_tracker = KillTracker(combat_timeout=10.0)

    def on_load(self):
        self.server.service_manager.register(
            "PlaceholderAPI", self._api, self, ServicePriority.HIGHEST
        )
        # Set the kill tracker in the API so it can register kill placeholders
        self._api.set_kill_tracker(self._kill_tracker)

    def on_enable(self):
        # Register event listener for kill tracking
        self.register_events(self)
        
        # Schedule periodic cleanup of old damage records (every 30 seconds)
        self.server.scheduler.run_task(
            self,
            lambda: self._kill_tracker.cleanup_old_damage_records(),
            delay=600,  # 30 seconds in ticks (20 ticks = 1 second)
            period=600   # Repeat every 30 seconds
        )

    def on_disable(self):
        self.server.service_manager.unregister_all(self)

    @event_handler
    def on_entity_damage_by_entity(self, event: EntityDamageByEntityEvent):
        """Track damage dealt by players to other players."""
        # Check if both the victim and damager are players
        if isinstance(event.entity, Player) and isinstance(event.damager, Player):
            victim = event.entity
            damager = event.damager
            
            # Don't track self-damage
            if victim.name != damager.name:
                self._kill_tracker.record_damage(victim, damager)

    @event_handler
    def on_player_death(self, event: PlayerDeathEvent):
        """Handle player death to track kills and reset killstreaks."""
        victim = event.entity
        
        # Get the valid killer (checks if damage is recent enough)
        killer_name = self._kill_tracker.get_valid_killer(victim)
        
        if killer_name:
            # Get the killer player object
            killer = self.server.get_player(killer_name)
            if killer and killer.is_online:
                # Add kill to the killer's count
                self._kill_tracker.add_kill(killer)
        
        # Always reset the victim's killstreak
        self._kill_tracker.reset_killstreak(victim)

    def on_command(
            self, sender: CommandSender, command: Command, args: list[str]
    ) -> bool:
        match args[0]:
            case "parse":
                assert len(args) == 3, f"Invalid number of arguments! Expected 3, got {len(args)}."
                match args[1]:
                    case "me":
                        if not isinstance(sender, Player):
                            sender.send_error_message("You must be a player to use 'me' as a target!")
                            return True

                        player = sender

                    case "--null":
                        player = None

                    case player_name:
                        player = self.server.get_player(player_name)
                        if player is None:
                            sender.send_error_message(f"Could not find player {player_name}!")
                            return True

                text: str = args[2]
                sender.send_message(self._api.set_placeholders(player, text))

            case "list":
                sender.send_message("Available placeholders:")
                for identifier in self._api.registered_identifiers:
                    sender.send_message(f"- {identifier}")

        return True
