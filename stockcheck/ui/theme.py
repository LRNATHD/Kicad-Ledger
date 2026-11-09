"""Theme and style helpers for KiCad-StockCheck."""

import wx

# Modern Clean Theme Colors
COLOR_BG = wx.Colour(248, 249, 250)
COLOR_CARD_BG = wx.Colour(255, 255, 255)
COLOR_BORDER = wx.Colour(222, 226, 230)
COLOR_TEXT_PRIMARY = wx.Colour(33, 37, 41)
COLOR_TEXT_MUTED = wx.Colour(108, 117, 125)

# Status Badge Colors
COLOR_SUCCESS = wx.Colour(40, 167, 69)      # In stock
COLOR_WARNING = wx.Colour(255, 153, 0)      # Low stock
COLOR_DANGER = wx.Colour(220, 53, 69)       # Missing
COLOR_INFO = wx.Colour(23, 162, 184)        # Compatible
COLOR_DNP = wx.Colour(140, 140, 140)        # DNP

# Highlight Row Colors
BG_IN_STOCK = wx.Colour(235, 247, 238)
BG_LOW_STOCK = wx.Colour(255, 248, 230)
BG_MISSING = wx.Colour(255, 235, 238)
BG_COMPATIBLE = wx.Colour(235, 245, 255)
BG_DNP = wx.Colour(245, 245, 245)


def get_status_color(status: str) -> wx.Colour:
    s = status.upper()
    if s == "IN_STOCK":
        return COLOR_SUCCESS
    elif s == "LOW_STOCK":
        return COLOR_WARNING
    elif s == "COMPATIBLE":
        return COLOR_INFO
    elif s == "DNP":
        return COLOR_DNP
    return COLOR_DANGER


def get_row_bg(status: str) -> wx.Colour:
    s = status.upper()
    if s == "IN_STOCK":
        return BG_IN_STOCK
    elif s == "LOW_STOCK":
        return BG_LOW_STOCK
    elif s == "COMPATIBLE":
        return BG_COMPATIBLE
    elif s == "DNP":
        return BG_DNP
    return BG_MISSING
