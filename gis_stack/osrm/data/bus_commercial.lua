-- Siva Gayathri Tours Commercial Fleet Routing Profile (Lua)
api_version = 4

Set = require('lib/set')
Sequence = require('lib/sequence')
Handlers = require("lib/way_handlers")
find_access_tag = require("lib/access").find_access_tag
limit = require("lib/maxspeed").limit
Utils = require("lib/utils")

function setup()
  return {
    properties = {
      max_speed_for_map_matching      = 100/3.6,
      weight_name                     = 'duration',
      process_call_tagless_node       = false,
      u_turn_penalty                  = 20,
      continue_straight_at_waypoint   = true,
      use_turn_restrictions          = true,
      left_hand_driving               = true  -- Left hand driving in India
    },

    default_mode              = mode.driving,
    default_speed             = 35,
    oneway_handling           = true,
    side_road_multiplier      = 0.8,
    turn_penalty              = 7.5,
    speed_reduction           = 0.8,

    -- Commercial vehicles (Buses, Tempo Travellers, Taxis) speed limits (km/h)
    speeds = Sequence {
      highway = {
        motorway        = 85,
        trunk           = 75,
        primary         = 60,
        secondary       = 50,
        tertiary        = 40,
        unclassified    = 30,
        residential     = 25,
        service         = 15
      }
    },

    service_penalties = {
      alley             = 0.5,
      parking           = 0.5,
      parking_aisle     = 0.5,
      driveway          = 0.5
    },

    restricted_highway_whitelist = Set {
      'motorway',
      'trunk',
      'primary',
      'secondary',
      'tertiary',
      'residential'
    },

    access_tag_whitelist = Set {
      'yes',
      'motorcar',
      'bus',
      'psv',
      'commercial',
      'taxi'
    }
  }
end

function process_way(profile, way, result, relations)
  local data = {
    highway = way:get_value_by_key('highway')
  }

  if not data.highway then
    return
  end

  local speed = profile.speeds.highway[data.highway] or profile.default_speed
  result.forward_speed = speed
  result.backward_speed = speed
  result.forward_mode = mode.driving
  result.backward_mode = mode.driving
end

function process_turn(profile, turn)
  turn.duration = 0.0
  if turn.angle >= 60 then
    turn.duration = turn.duration + 4.0
  end
  if turn.is_u_turn then
    turn.duration = turn.duration + profile.properties.u_turn_penalty
  end
end

return {
  setup = setup,
  process_way = process_way,
  process_turn = process_turn
}
