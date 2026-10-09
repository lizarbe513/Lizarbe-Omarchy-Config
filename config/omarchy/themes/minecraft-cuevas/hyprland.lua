local active_border_color = "#A46BE0"
local inactive_border_color = "#2C2640"

hl.config({
  general = {
    gaps_in = 6,
    gaps_out = 12,
    border_size = 2,
    col = {
      active_border = active_border_color,
      inactive_border = inactive_border_color,
    },
  },

  decoration = {
    rounding = 0,
    shadow = {
      enabled = false,
    },
  },

  group = {
    col = {
      border_active = active_border_color,
      border_inactive = inactive_border_color,
    },
  },
})
