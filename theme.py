import flet as ft

def glass_border(color="#30FFFFFF", width=1):
    side = ft.BorderSide(width, color)
    return ft.Border(
        left=side,
        top=side,
        right=side,
        bottom=side
    )

BG_PRIMARY = "#0F172A"
BG_SECONDARY = "#111827"
BG_TERTIARY = "#1E293B"

ACCENT = "#3B82F6"          
ACCENT_PURPLE = "#8B5CF6"   
ACCENT_GREEN = "#10B981"    

TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#CBD5E1"

MUTED = "#94A3B8"

GLASS_BG = "#14FFFFFF"
GLASS_BG_SOFT = "#0BFFFFFF"

GLASS_BORDER = glass_border("#30FFFFFF")

GLASS_SHADOW = ft.BoxShadow(
    blur_radius=50,
    spread_radius=-12,
    color="#40000000",
    offset=ft.Offset(0, 24)
)

CARD_RADIUS = 36 

QUOTES = [
    "Great results require great ambitions",
    "The pain you feel today will be the strength you feel tomorrow",
    "Focus on the process, not the outcome",
    "One day, or day one. You decide.",
    "Discipline is choosing between what you want now and what you want most.",
    "Push yourself, because no one else is going to do it for you.",
    "Success is the sum of small efforts, repeated day in and day out.",
    "Don't stop until you're proud."
]
