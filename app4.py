import io
import json
import os
import re
import sqlite3
import unicodedata
import uuid
from datetime import date, datetime

import pandas as pd
import streamlit as st
from geopy.geocoders import Nominatim
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from streamlit_geolocation import streamlit_geolocation

# UI EDITING: Configure Streamlit page title, icon, and wide desktop/mobile responsive layout
st.set_page_config(
    page_title="Explorer Quest: Lyon Edition",
    page_icon="🦁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# LOGIC: Define persistent storage paths for SQLite database and Explorer uploaded media
DB_PATH = "explorer_lyon.db"
MEDIA_DIR = "explorer_media"
os.makedirs(MEDIA_DIR, exist_ok=True)


# ==============================================================================
# 1. CURATED DATA: LYON GUIDE, 12 RIDDLES, 3 PHOTO QUESTS, THEMES, FONTS, COUPONS
# ==============================================================================

# UI EDITING: Curated Lyon Location Hub sections with French primary titles and English subtitles
LYON_GUIDE_SECTIONS = [
    {
        "title_fr": "Histoire de Lugdunum & Fourvière",
        "title_en": "History of Lugdunum & Fourvière",
        "badge": "43 AV. J.-C. • UNESCO",
        "summary": (
            "Founded in 43 BC by Roman consul Lucius Munatius Plancus as Colonia Copia Felix Munatia "
            "(Lugdunum), Lyon served as the capital of the Three Gauls. Rising above the Saône river, "
            "Fourvière Hill ('the hill that prays') crowns the city with ancient Roman theatres and the "
            "19th-century Basilica of Notre-Dame de Fourvière, while the Presqu'île peninsula between the "
            "Rhône and Saône showcases grand Haussmannian boulevards and Place Bellecour."
        ),
        "highlights": [
            "Colline de Fourvière & Basilique Notre-Dame",
            "Presqu'île & Place Bellecour",
            "Lugdunum — Musée et Théâtres Romains",
        ],
    },
    {
        "title_fr": "Insolite : Les Mystérieuses Traboules",
        "title_en": "Cool Facts: The Secret Traboules Passages",
        "badge": "PASSAGES SECRETS",
        "summary": (
            "Originating from the Latin 'trans ambulare' (to walk through), Lyon's ~400 traboules are "
            "hidden architectural corridors connecting street to street through Renaissance courtyards and "
            "spiral stone staircases. Originally built in Vieux Lyon for residents to reach the Saône for "
            "water, they later allowed Croix-Rousse silk workers (Canuts) to transport delicate fabrics "
            "sheltered from rain—and sheltered French Resistance fighters during WWII."
        ),
        "highlights": [
            "La Longue Traboule (54 Rue Saint-Jean to 27 Rue du Bœuf)",
            "Cour des Voraces (Croix-Rousse landmark)",
            "Tour Rose (22 Rue du Bœuf)",
        ],
    },
    {
        "title_fr": "Architecture & Patrimoine Urbain",
        "title_en": "Architecture & Urban Heritage",
        "badge": "RENAISSANCE À AVANT-GARDE",
        "summary": (
            "Over 500 hectares of central Lyon are inscribed as a UNESCO World Heritage site, spanning "
            "2,000 years of uninterrupted urban evolution. Walk from Italianate ochre-and-rose Renaissance "
            "facades in Vieux Lyon to the soaring industrial ateliers of La Croix-Rousse, and finish at "
            "the futuristic deconstructivist crystal-and-steel Musée des Confluences where the two rivers meet."
        ),
        "highlights": [
            "Vieux Lyon Renaissance Courtyards",
            "Opéra Nouvel & Hôtel de Ville (Place des Terreaux)",
            "Musée des Confluences at the Rhône-Saône Tip",
        ],
    },
    {
        "title_fr": "Gastronomie & Bouchons Lyonnais",
        "title_en": "Gastronomy & Traditional Bouchons",
        "badge": "CAPITALE DE LA GASTRONOMIE",
        "summary": (
            "Crowned World Capital of Gastronomy in 1935 by food critic Curnonsky and immortalized by "
            "three-Michelin-star legend Paul Bocuse, Lyon celebrates hearty, convivial dining in certified "
            "'Bouchons Lyonnais'. Expect red-and-white checkered tablecloths, 46cl 'pots lyonnais' of "
            "Beaujolais wine, and iconic specialties crafted by the historic 'Mères Lyonnaises'."
        ),
        "highlights": [
            "Quenelles de Brochet Sauce Nantua & Salade Lyonnaise",
            "Cervelle de Canut, Tablier de Sapeur & Tarte à la Praline",
            "Les Halles de Lyon Paul Bocuse & Rue Mercière",
        ],
    },
    {
        "title_fr": "Festivals & La Fête des Lumières",
        "title_en": "Festivals & The Festival of Lights",
        "badge": "8 DÉCEMBRE • ILLUMINATIONS",
        "summary": (
            "Every December around the 8th, millions of visitors gather as Lyon transforms into an open-air "
            "canvas of monumental light installations. Born in 1852 when Lyonnais residents spontaneously placed "
            "candles ('lumignons') in colored glass jars on their windowsills to celebrate the inauguration of "
            "the golden statue of the Virgin Mary atop Fourvière, the tradition remains Lyon's brightest celebration."
        ),
        "highlights": [
            "Place des Terreaux & Bartholdi Fountain Light Shows",
            "Illuminated Basilica of Fourvière & Saint-Jean Cathedral",
            "Les Nuits de Fourvière Summer Performing Arts Festival",
        ],
    },
]

# UI EDITING: Interactive visual landmark cards with high-resolution imagery and fallback styling
LYON_LANDMARK_CARDS = [
    {
        "name_fr": "Basilique Notre-Dame de Fourvière",
        "name_en": "Basilica of Notre-Dame de Fourvière",
        "district": "Fourvière (5e)",
        "tag": "PANORAMA & SACRED ART",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/Basilique_Notre-Dame_de_Fourvi%C3%A8re_Lyon.jpg/800px-Basilique_Notre-Dame_de_Fourvi%C3%A8re_Lyon.jpg",
        "caption": "Built 1872–1884 by Pierre Bossan, blending Romano-Byzantine mosaics with panoramic views over Lyon.",
    },
    {
        "name_fr": "Vieux Lyon & Les Traboules",
        "name_en": "Old Lyon & Renaissance Passages",
        "district": "Saint-Jean (5e)",
        "tag": "UNESCO RENAISSANCE",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Lyon_5e_-_Rue_Saint-Jean_et_Cath%C3%A9drale.jpg/800px-Lyon_5e_-_Rue_Saint-Jean_et_Cath%C3%A9drale.jpg",
        "caption": "Cobblestone alleys, Gothic Saint-Jean Cathedral, and vaulted secret passageways.",
    },
    {
        "name_fr": "Place Bellecour & Presqu'île",
        "name_en": "Bellecour Square & The Peninsula",
        "district": "Bellecour (2e)",
        "tag": "HEART OF LYON",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/Place_Bellecour_Lyon.jpg/800px-Place_Bellecour_Lyon.jpg",
        "caption": "Europe's largest pedestrian square, featuring red crushed-brick gravel and King Louis XIV on horseback.",
    },
    {
        "name_fr": "Parc de la Tête d'Or",
        "name_en": "Park of the Golden Head",
        "district": "Tête d'Or (6e)",
        "tag": "117-HECTARE URBAN OASIS",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/Parc_de_la_T%C3%AAte_d%27Or_-_Lac.jpg/800px-Parc_de_la_T%C3%AAte_d%27Or_-_Lac.jpg",
        "caption": "France's largest urban park featuring a 16-hectare boating lake, botanical greenhouses, and rose gardens.",
    },
    {
        "name_fr": "Musée des Confluences",
        "name_en": "Confluences Science & Anthropology Museum",
        "district": "La Confluence (2e)",
        "tag": "RHÔNE MEETS SAÔNE",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/03/Mus%C3%A9e_des_Confluences_Lyon.jpg/800px-Mus%C3%A9e_des_Confluences_Lyon.jpg",
        "caption": "Coop Himmelb(l)au's glass-and-steel 'Crystal Cloud' poised where the Rhône and Saône unite.",
    },
    {
        "name_fr": "Théâtres Romains de Fourvière",
        "name_en": "Ancient Roman Theatres of Fourvière",
        "district": "Fourvière (5e)",
        "tag": "15 BC LUGDUNUM",
        "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Th%C3%A9%C3%A2tre_antique_de_Lyon.jpg/800px-Th%C3%A9%C3%A2tre_antique_de_Lyon.jpg",
        "caption": "The oldest Roman theatre in Gaul, seating 10,000 spectators and still hosting summer concerts.",
    },
]

# LOGIC: Hardcoded list of 12 curated Lyon riddles & trivia challenges (50 points each)
LYON_RIDDLES = [
    {
        "id": "riddle_01",
        "topic_fr": "Les Traboules de Lyon",
        "topic_en": "The Hidden Traboules Passages",
        "riddle": (
            "I am neither an avenue nor a bridge, yet I let silk weavers cross entire city blocks dry "
            "beneath spiral stone stairs and secret Renaissance courtyards. What architectural secret of Lyon am I?"
        ),
        "hint": "Derived from Latin 'trans ambulare', Vieux Lyon and Croix-Rousse hide over 400 of me.",
        "accepted_answers": ["traboule", "traboules", "les traboules", "une traboule"],
        "fun_fact": (
            "Lyon has roughly 400 traboules! During World War II, Jean Moulin and the French Resistance used "
            "their labyrinthine exits to evade Gestapo patrols."
        ),
        "points": 50,
    },
    {
        "id": "riddle_02",
        "topic_fr": "La Confluence du Rhône et de la Saône",
        "topic_en": "Confluence of the Rhône & Saône Rivers",
        "riddle": (
            "Locals call me the fiery, Alpine brother who rushes south to embrace my gentle, Burgundy sister "
            "at the southern tip of the Presqu'île. Name the two rivers that unite in Lyon (give both names)."
        ),
        "hint": "One flows from the Swiss Alps; the other flows calmly from the Vosges through Burgundy.",
        "accepted_answers": [
            "rhone and saone",
            "saone and rhone",
            "rhone & saone",
            "saone & rhone",
            "le rhone et la saone",
            "rhone saone",
            "saone rhone",
        ],
        "fun_fact": (
            "In French, 'le Rhône' is masculine and 'la Saône' is feminine—poets in Lyon celebrate their "
            "meeting at La Confluence as an eternal marriage of two contrasting currents."
        ),
        "points": 50,
    },
    {
        "id": "riddle_03",
        "topic_fr": "Guignol le Canut",
        "topic_en": "Guignol, Lyon's Iconic Puppet",
        "riddle": (
            "Born in 1808 from the hands of out-of-work dentist Laurent Mourguet, I wear a braided queue, "
            "a black tricorn hat, and defend ordinary silk workers with sharp wit and a wooden slapstick. Who am I?"
        ),
        "hint": "I am France's most famous hand puppet, born in Vieux Lyon.",
        "accepted_answers": ["guignol", "le guignol"],
        "fun_fact": (
            "Laurent Mourguet originally created Guignol to distract patients while pulling teeth before "
            "turning puppetry into biting social satire for Lyon's working class."
        ),
        "points": 50,
    },
    {
        "id": "riddle_04",
        "topic_fr": "Paul Bocuse, Pape de la Gastronomie",
        "topic_en": "Paul Bocuse, Pope of Gastronomy",
        "riddle": (
            "I held three Michelin stars for over half a century, gave my name to Lyon's premier indoor food "
            "market, and founded the world's most prestigious culinary competition. Who am I?"
        ),
        "hint": "Known worldwide as 'Monsieur Paul', born in Collonges-au-Mont-d'Or just north of Lyon.",
        "accepted_answers": ["paul bocuse", "bocuse", "monsieur paul"],
        "fun_fact": (
            "Paul Bocuse's flagship restaurant L'Auberge du Pont de Collonges held three Michelin stars for "
            "53 consecutive years (1965–2018), and Les Halles de Lyon proudly bears his name."
        ),
        "points": 50,
    },
    {
        "id": "riddle_05",
        "topic_fr": "Les Canuts de la Croix-Rousse",
        "topic_en": "The Canuts Silk Weavers of Croix-Rousse",
        "riddle": (
            "We worked 14-hour days atop 'the hill that works' with 4-meter-high ceilings built to house our "
            "Jacquard looms, and our 1831 uprising inspired modern labor movements. What were Lyon's master silk weavers called?"
        ),
        "hint": "A famous fresh herb cheese dip ('Cervelle de ___') is also named after us!",
        "accepted_answers": ["canuts", "canut", "les canuts", "silk weavers"],
        "fun_fact": (
            "The Croix-Rousse district features specially engineered 4-meter-high apartment ceilings solely "
            "so master Canuts could install towering wooden Jacquard silk looms inside their homes."
        ),
        "points": 50,
    },
    {
        "id": "riddle_06",
        "topic_fr": "Basilique Notre-Dame de Fourvière",
        "topic_en": "Basilica of Notre-Dame de Fourvière",
        "riddle": (
            "Affectionately nicknamed 'the upside-down elephant' by locals because of my four corner towers "
            "pointing skyward, I watch over Lyon from its western hilltop. What monument am I?"
        ),
        "hint": "A golden statue of the Virgin Mary gleams atop my chapel bell tower.",
        "accepted_answers": [
            "fourviere",
            "notre dame de fourviere",
            "basilique notre dame de fourviere",
            "basilica of notre dame de fourviere",
            "basilica of fourviere",
            "notre-dame de fourviere",
        ],
        "fun_fact": (
            "Locals fondly joke that Fourvière Basilica looks like an upside-down elephant lying on its back "
            "with its four octagonal towers sticking up like legs!"
        ),
        "points": 50,
    },
    {
        "id": "riddle_07",
        "topic_fr": "La Place Bellecour",
        "topic_en": "Place Bellecour",
        "riddle": (
            "Covered in distinctive red crushed-tile gravel, devoid of trees, and guarded by a bronze equestrian "
            "statue of King Louis XIV, I am the largest pedestrian square in Europe. What is my name?"
        ),
        "hint": "All road distances from Lyon are measured from 'Kilometer Zero' on my square.",
        "accepted_answers": ["place bellecour", "bellecour", "la place bellecour"],
        "fun_fact": (
            "Measuring 62,000 square meters, Place Bellecour is larger than Red Square in Moscow and serves "
            "as Lyon's official 'Kilometer Zero' geographic reference point."
        ),
        "points": 50,
    },
    {
        "id": "riddle_08",
        "topic_fr": "Le Parc de la Tête d'Or",
        "topic_en": "Parc de la Tête d'Or",
        "riddle": (
            "Legend says a treasure—a golden bust of Christ buried by Crusaders—lies hidden beneath my soil. "
            "Today I span 117 hectares with a boating lake, botanical garden, and rose garden. Name this park."
        ),
        "hint": "Literally translates to 'Park of the Golden Head' in Lyon's 6th arrondissement.",
        "accepted_answers": [
            "parc de la tete dor",
            "parc de la tete d or",
            "tete dor",
            "tete d or",
            "park of the golden head",
        ],
        "fun_fact": (
            "Opened in 1857—the same year as New York's Central Park—Parc de la Tête d'Or boasts over "
            "16,000 rose bushes across 450 varieties and one of France's oldest botanical gardens."
        ),
        "points": 50,
    },
    {
        "id": "riddle_09",
        "topic_fr": "Les Frères Lumière",
        "topic_en": "The Lumière Brothers",
        "riddle": (
            "In 1895, on Rue du Premier-Film in Lyon's Monplaisir district, two brothers filmed workers "
            "leaving their photographic factory using their patented Cinématographe. What was their family surname?"
        ),
        "hint": "Their French surname literally translates to 'Light'.",
        "accepted_answers": ["lumiere", "freres lumiere", "lumiere brothers", "les freres lumiere"],
        "fun_fact": (
            "Auguste and Louis Lumière shot the very first motion picture in history—'La Sortie de l'Usine "
            "Lumière à Lyon'—right outside their factory hangar, which still stands today as the Institut Lumière."
        ),
        "points": 50,
    },
    {
        "id": "riddle_10",
        "topic_fr": "La Fête des Lumières",
        "topic_en": "The Festival of Lights",
        "riddle": (
            "Every December 8th since 1852, Lyonnais place glowing candles called 'lumignons' on every windowsill, "
            "sparking a four-night festival that draws millions. What is this famous festival called?"
        ),
        "hint": "In French, 'Festival of Lights'.",
        "accepted_answers": [
            "fete des lumieres",
            "la fete des lumieres",
            "festival of lights",
            "festival of light",
        ],
        "fun_fact": (
            "In 1852, fierce storms threatened to cancel the inauguration of Fourvière's golden Virgin Mary "
            "statue—until the skies suddenly cleared at dusk and citizens lit thousands of window candles in joy."
        ),
        "points": 50,
    },
    {
        "id": "riddle_11",
        "topic_fr": "Les Théâtres Romains de Fourvière",
        "topic_en": "The Roman Theatres of Fourvière",
        "riddle": (
            "Built around 15 BC under Emperor Augustus when Lyon was known as Lugdunum, my stone semicircular "
            "tiers still echo with music every summer. What ancient Roman landmark am I?"
        ),
        "hint": "I sit beside a smaller Odeon on Fourvière Hill and host 'Les Nuits de Fourvière'.",
        "accepted_answers": [
            "roman theatre",
            "roman theatres",
            "theatre antique",
            "theatres romains",
            "theatre romain",
            "roman theater",
            "roman theaters",
            "ancient theatre of fourviere",
        ],
        "fun_fact": (
            "Constructed in 15 BC, the Grand Théâtre de Fourvière is the oldest Roman theatre in all of "
            "ancient Gaul and was rediscovered under vineyards only in the 19th and 20th centuries."
        ),
        "points": 50,
    },
    {
        "id": "riddle_12",
        "topic_fr": "Les Bouchons Lyonnais",
        "topic_en": "Authentic Lyonnais Bouchons",
        "riddle": (
            "Named after the bundles of straw once hung outside inns to wipe down travelers' horses, I am "
            "Lyon's quintessential cozy tavern serving quenelles, tablier de sapeur, and Beaujolais. What am I?"
        ),
        "hint": "The French word also means 'cork' or 'traffic jam'.",
        "accepted_answers": ["bouchon", "bouchons", "bouchon lyonnais", "bouchons lyonnais", "les bouchons"],
        "fun_fact": (
            "Only around 20–25 restaurants in Lyon hold the official 'Authentiques Bouchons Lyonnais' label, "
            "certifying homemade recipes, warm hospitality, and traditional thick-bottomed 46cl 'pots lyonnais'."
        ),
        "points": 50,
    },
]

# LOGIC: 3 Real-Life Photo Quests in Lyon (200 points each)
LYON_PHOTO_QUESTS = [
    {
        "id": "quest_01",
        "title_fr": "Quête I : Le Passage Secret des Traboules",
        "title_en": "Quest I: The Secret Traboule Passage",
        "location_tag": "Vieux Lyon / Croix-Rousse",
        "instructions": (
            "Locate an authentic hidden Traboule passage in Vieux Lyon (such as 54 Rue Saint-Jean) or "
            "Croix-Rousse (Cour des Voraces), capture a photo of its vaulted stone corridor or courtyard, "
            "and log your Explorer proof below."
        ),
        "points": 200,
    },
    {
        "id": "quest_02",
        "title_fr": "Quête II : Le Panorama de Fourvière",
        "title_en": "Quest II: The Fourvière Esplanade Panorama",
        "location_tag": "Basilique de Fourvière",
        "instructions": (
            "Ascend Fourvière Hill by funicular or foot to the Basilica esplanade, photograph the sweeping "
            "view across Lyon's terracotta rooftops and the Rhône valley, and upload your proof."
        ),
        "points": 200,
    },
    {
        "id": "quest_03",
        "title_fr": "Quête III : La Fresque des Lyonnais",
        "title_en": "Quest III: The Famous Lyonnais Trompe-l'Œil Mural",
        "location_tag": "Quai Saint-Vincent (1er)",
        "instructions": (
            "Find the monumental 'Fresque des Lyonnais' mural at 2 Rue de la Martinière overlooking the Saône, "
            "snap a photo featuring Paul Bocuse, Antoine de Saint-Exupéry, or the Lumière brothers, and log it!"
        ),
        "points": 200,
    },
]

# UI EDITING: 10 Album Visual Themes with HTML/CSS preview tokens & ReportLab PDF color palettes
ALBUM_THEMES = {
    "Vintage Map": {
        "bg": "#F4EBD9",
        "card_bg": "#FAF3E3",
        "border": "#8B5A2B",
        "accent": "#A0522D",
        "text": "#3B2818",
        "subtext": "#6E4E32",
        "border_style": "double",
        "badge_bg": "#8B5A2B",
        "badge_text": "#FAF3E3",
    },
    "Cyberpunk Neon": {
        "bg": "#0B0E17",
        "card_bg": "#13192B",
        "border": "#00F5D4",
        "accent": "#FF2A85",
        "text": "#E0F7FA",
        "subtext": "#80DEEA",
        "border_style": "solid",
        "badge_bg": "#FF2A85",
        "badge_text": "#FFFFFF",
    },
    "Minimalist Journal": {
        "bg": "#FAFAFA",
        "card_bg": "#FFFFFF",
        "border": "#D4D4D8",
        "accent": "#18181B",
        "text": "#18181B",
        "subtext": "#52525B",
        "border_style": "solid",
        "badge_bg": "#27272A",
        "badge_text": "#FAFAFA",
    },
    "Golden Hour": {
        "bg": "#FFF3E0",
        "card_bg": "#FFF8EE",
        "border": "#E65100",
        "accent": "#D84315",
        "text": "#3E1F0D",
        "subtext": "#7A3E1D",
        "border_style": "solid",
        "badge_bg": "#EF6C00",
        "badge_text": "#FFFFFF",
    },
    "Editorial Magazine": {
        "bg": "#F5F5F4",
        "card_bg": "#FFFFFF",
        "border": "#1C1917",
        "accent": "#991B1B",
        "text": "#1C1917",
        "subtext": "#44403C",
        "border_style": "solid",
        "badge_bg": "#991B1B",
        "badge_text": "#FFFFFF",
    },
    "Retro Stamp": {
        "bg": "#EFE6D5",
        "card_bg": "#FBF7EF",
        "border": "#2B547E",
        "accent": "#B22222",
        "text": "#1F2D3D",
        "subtext": "#4A607A",
        "border_style": "dashed",
        "badge_bg": "#B22222",
        "badge_text": "#FBF7EF",
    },
    "Dark Elegance": {
        "bg": "#121212",
        "card_bg": "#1D1B18",
        "border": "#D4AF37",
        "accent": "#E5C158",
        "text": "#F5EFE0",
        "subtext": "#C5B38A",
        "border_style": "double",
        "badge_bg": "#D4AF37",
        "badge_text": "#121212",
    },
    "Pop Art": {
        "bg": "#FFE600",
        "card_bg": "#FFFFFF",
        "border": "#000000",
        "accent": "#E60023",
        "text": "#000000",
        "subtext": "#222222",
        "border_style": "solid",
        "badge_bg": "#0057FF",
        "badge_text": "#FFFFFF",
    },
    "Botanical Travel": {
        "bg": "#E8F0E6",
        "card_bg": "#F6FAF5",
        "border": "#2D5A27",
        "accent": "#3B7A34",
        "text": "#1B3618",
        "subtext": "#456940",
        "border_style": "solid",
        "badge_bg": "#2D5A27",
        "badge_text": "#F6FAF5",
    },
    "Classic Blueprint": {
        "bg": "#0D3B66",
        "card_bg": "#134B80",
        "border": "#A9D6E5",
        "accent": "#FFFFFF",
        "text": "#F0F8FF",
        "subtext": "#BDE0FE",
        "border_style": "dashed",
        "badge_bg": "#A9D6E5",
        "badge_text": "#0D3B66",
    },
}

# UI EDITING: 10 Google Fonts mapped to CSS font families and ReportLab base PDF typefaces
GOOGLE_FONTS_MAP = {
    "Cinzel": {"css": "'Cinzel', serif", "pdf_font": "Times-Roman", "pdf_bold": "Times-Bold"},
    "Playfair Display": {"css": "'Playfair Display', serif", "pdf_font": "Times-Roman", "pdf_bold": "Times-Bold"},
    "Space Grotesk": {"css": "'Space Grotesk', sans-serif", "pdf_font": "Helvetica", "pdf_bold": "Helvetica-Bold"},
    "Caveat": {"css": "'Caveat', cursive", "pdf_font": "Times-Italic", "pdf_bold": "Times-BoldItalic"},
    "Lobster": {"css": "'Lobster', cursive", "pdf_font": "Times-BoldItalic", "pdf_bold": "Times-Bold"},
    "Montserrat": {"css": "'Montserrat', sans-serif", "pdf_font": "Helvetica", "pdf_bold": "Helvetica-Bold"},
    "Pacifico": {"css": "'Pacifico', cursive", "pdf_font": "Times-Italic", "pdf_bold": "Times-BoldItalic"},
    "Oswald": {"css": "'Oswald', sans-serif", "pdf_font": "Helvetica-Bold", "pdf_bold": "Helvetica-Bold"},
    "Syne": {"css": "'Syne', sans-serif", "pdf_font": "Helvetica-Bold", "pdf_bold": "Helvetica-Bold"},
    "Special Elite": {"css": "'Special Elite', monospace", "pdf_font": "Courier", "pdf_bold": "Courier-Bold"},
}

# LOGIC: Real-World Lyon Coupon Store catalog redeemable with earned Explorer points
COUPON_CATALOG = [
    {
        "id": "cpn_bouchon",
        "merchant": "Bouchon Aux Trois Cochons (Vieux Lyon)",
        "title_fr": "Tarte à la Praline & Kir Lyonnais Offerts",
        "title_en": "Complimentary Praline Tart & Kir Lyonnais",
        "category": "Bouchon Gastronomique",
        "cost": 150,
        "details": "Valid with any traditional Lyonnais menu at Rue Saint-Jean, Lyon 5e.",
    },
    {
        "id": "cpn_halles",
        "merchant": "Les Halles de Lyon Paul Bocuse",
        "title_fr": "Coffret Dégustation Saint-Marcellin & Rosette",
        "title_en": "Artisanal Saint-Marcellin Cheese & Rosette Tasting Box",
        "category": "Marché Gourmet",
        "cost": 250,
        "details": "Redeemable at participating affineur & charcuterie counters, Cours Lafayette.",
    },
    {
        "id": "cpn_silk",
        "merchant": "Atelier Soierie Saint-Georges (Croix-Rousse)",
        "title_fr": "-25% sur un Carré de Soie Lyonnais",
        "title_en": "25% Off Hand-Printed Lyon Silk Scarf",
        "category": "Boutique Artisanale",
        "cost": 300,
        "details": "Includes private demonstration of a historic 19th-century Jacquard loom.",
    },
    {
        "id": "cpn_cruise",
        "merchant": "Les Bateaux Lyonnais — Quai des Célestins",
        "title_fr": "Croisière Découverte Rhône & Saône (1 Place)",
        "title_en": "1-Hour Rhône & Saône Sightseeing River Cruise Pass",
        "category": "Expérience Fluviale",
        "cost": 400,
        "details": "Panoramic guided cruise from Bellecour to Musée des Confluences.",
    },
    {
        "id": "cpn_hotel",
        "merchant": "Hôtel & Spa Cour des Loges — Vieux Lyon",
        "title_fr": "Bon Privilège de 50 € sur une Nuit Renaissance",
        "title_en": "€50 Heritage Stay & Thermal Spa Voucher",
        "category": "Hôtel de Charme",
        "cost": 650,
        "details": "Valid on direct weekend bookings in the heart of UNESCO Vieux Lyon.",
    },
]


# ==============================================================================
# 2. SQLITE DATABASE PERSISTENCE & RANKING ENGINE
# ==============================================================================

# LOGIC: Determine Explorer tier rank from total earned points
def compute_explorer_tier(total_points: int) -> tuple[str, str]:
    if total_points >= 900:
        return ("Premium Legend", "Légende de Lugdunum")
    elif total_points >= 500:
        return ("Elite Explorer", "Explorateur d'Élite")
    elif total_points >= 200:
        return ("Adventurer", "Aventurier de Lyon")
    return ("Rookie Explorer", "Explorateur Débutant")


# LOGIC: Initialize SQLite database (explorer_lyon.db) with explorer_profile and diary_entries tables
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS explorer_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            explorer_name TEXT NOT NULL DEFAULT 'Explorer',
            total_points INTEGER NOT NULL DEFAULT 0,
            spent_points INTEGER NOT NULL DEFAULT 0,
            tier_rank TEXT NOT NULL DEFAULT 'Rookie Explorer',
            solved_riddles TEXT NOT NULL DEFAULT '[]',
            completed_quests TEXT NOT NULL DEFAULT '[]',
            redeemed_coupons TEXT NOT NULL DEFAULT '[]'
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS diary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            lyon_spot TEXT NOT NULL,
            diary_text TEXT NOT NULL,
            image_path TEXT,
            album_theme TEXT NOT NULL,
            album_font TEXT NOT NULL
        )
        """
    )
    # LOGIC: Ensure single default Explorer row exists on first launch
    cursor.execute("SELECT COUNT(*) FROM explorer_profile WHERE id = 1")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            """
            INSERT INTO explorer_profile
            (id, explorer_name, total_points, spent_points, tier_rank, solved_riddles, completed_quests, redeemed_coupons)
            VALUES (1, 'Explorer', 0, 0, 'Rookie Explorer', '[]', '[]', '[]')
            """
        )
    conn.commit()
    conn.close()


# LOGIC: Fetch Explorer profile state from SQLite
def load_profile() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT explorer_name, total_points, spent_points, tier_rank,
               solved_riddles, completed_quests, redeemed_coupons
        FROM explorer_profile WHERE id = 1
        """
    )
    row = cursor.fetchone()
    conn.close()
    return {
        "explorer_name": row[0],
        "total_points": row[1],
        "spent_points": row[2],
        "tier_rank": row[3],
        "solved_riddles": json.loads(row[4]),
        "completed_quests": json.loads(row[5]),
        "redeemed_coupons": json.loads(row[6]),
    }


# LOGIC: Persist updated Explorer profile state to SQLite
def save_profile(profile: dict):
    tier_en, _ = compute_explorer_tier(profile["total_points"])
    profile["tier_rank"] = tier_en
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE explorer_profile
        SET explorer_name = ?,
            total_points = ?,
            spent_points = ?,
            tier_rank = ?,
            solved_riddles = ?,
            completed_quests = ?,
            redeemed_coupons = ?
        WHERE id = 1
        """,
        (
            profile["explorer_name"],
            profile["total_points"],
            profile["spent_points"],
            profile["tier_rank"],
            json.dumps(profile["solved_riddles"]),
            json.dumps(profile["completed_quests"]),
            json.dumps(profile["redeemed_coupons"]),
        ),
    )
    conn.commit()
    conn.close()


# LOGIC: Insert a new travel diary entry into SQLite
def add_diary_entry(entry_date: str, lyon_spot: str, diary_text: str, image_path: str, theme: str, font: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO diary_entries (entry_date, lyon_spot, diary_text, image_path, album_theme, album_font)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (entry_date, lyon_spot, diary_text, image_path, theme, font),
    )
    conn.commit()
    conn.close()


# LOGIC: Load all saved diary entries ordered newest first
def load_diary_entries() -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, entry_date, lyon_spot, diary_text, image_path, album_theme, album_font
        FROM diary_entries
        ORDER BY entry_date DESC, id DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "entry_date": r[1],
            "lyon_spot": r[2],
            "diary_text": r[3],
            "image_path": r[4],
            "album_theme": r[5],
            "album_font": r[6],
        }
        for r in rows
    ]


# LOGIC: Delete a specific diary entry by ID
def delete_diary_entry(entry_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM diary_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()


# LOGIC: Save uploaded image bytes cleanly to explorer_media/ and return relative path
def persist_uploaded_image(uploaded_file, prefix: str = "diary") -> str:
    if uploaded_file is None:
        return ""
    ext = os.path.splitext(uploaded_file.name)[1].lower() or ".jpg"
    if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        ext = ".jpg"
    filename = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{ext}"
    filepath = os.path.join(MEDIA_DIR, filename)
    img = PILImage.open(uploaded_file).convert("RGB")
    img.save(filepath, format="JPEG", quality=90)
    return filepath


# ==============================================================================
# 3. GPS REVERSE-GEOCODING, RIDDLE MATCHING & PDF ALBUM RENDERING
# ==============================================================================

# LOGIC: Reverse-geocode GPS coordinates via Nominatim with session caching and Lyon geofence verification
def reverse_geocode_location(lat: float, lon: float) -> dict:
    cache_key = f"{round(lat, 5)}_{round(lon, 5)}"
    if "geo_cache" not in st.session_state:
        st.session_state["geo_cache"] = {}
    if cache_key in st.session_state["geo_cache"]:
        return st.session_state["geo_cache"][cache_key]

    try:
        geolocator = Nominatim(user_agent="explorer_quest_lyon_edition_v1")
        location_info = geolocator.reverse((lat, lon), exactly_one=True, language="en", timeout=8)
        address = location_info.raw.get("address", {}) if location_info else {}
        district = (
            address.get("suburb")
            or address.get("neighbourhood")
            or address.get("city_district")
            or address.get("quarter")
            or ""
        )
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("county")
            or "Unknown City"
        )
        country = address.get("country") or "Unknown Country"
        country_code = address.get("country_code", "").lower()

        if district and district.lower() != city.lower():
            formatted_place = f"{district}, {city}, {country}"
        else:
            formatted_place = f"{city}, {country}"

        # LOGIC: Verify whether coordinates fall inside Greater Lyon, France
        in_lyon_bbox = (45.68 <= lat <= 45.84) and (4.75 <= lon <= 4.95)
        in_lyon_name = ("lyon" in city.lower()) and ("france" in country.lower() or country_code == "fr")
        is_lyon = bool(in_lyon_bbox or in_lyon_name)

        result = {
            "formatted_place": formatted_place,
            "district": district,
            "city": city,
            "country": country,
            "is_lyon": is_lyon,
        }
    except Exception:
        # LOGIC: Fallback coordinate bounding-box check if offline or Nominatim rate-limited
        is_lyon = (45.68 <= lat <= 45.84) and (4.75 <= lon <= 4.95)
        formatted_place = "Lyon, France" if is_lyon else f"Lat {lat:.4f}, Lon {lon:.4f}"
        result = {
            "formatted_place": formatted_place,
            "district": "",
            "city": "Lyon" if is_lyon else "Detected Coordinates",
            "country": "France" if is_lyon else "Earth",
            "is_lyon": is_lyon,
        }

    st.session_state["geo_cache"][cache_key] = result
    return result


# LOGIC: Normalize user riddle answers (strip accents, punctuation, and French/English articles)
def normalize_text(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.strip().lower())
    ascii_only = "".join(c for c in nfkd if not unicodedata.combining(c))
    cleaned = re.sub(r"[^a-z0-9\s]", " ", ascii_only)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    for prefix in ("the ", "a ", "an ", "le ", "la ", "les ", "l ", "un ", "une ", "des "):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :].strip()
    return cleaned


def check_riddle_answer(user_input: str, accepted_answers: list[str]) -> bool:
    norm_user = normalize_text(user_input)
    if not norm_user:
        return False
    norm_accepted = {normalize_text(ans) for ans in accepted_answers}
    return norm_user in norm_accepted


# LOGIC: Sanitize UTF-8 strings for ReportLab WinAnsiEncoding (preserves French accents safely)
def pdf_safe_text(text: str) -> str:
    replacements = {
        "œ": "oe",
        "Œ": "OE",
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
        "—": "-",
        "–": "-",
        "…": "...",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("cp1252", errors="replace").decode("cp1252")


# LOGIC: Generate styled multi-entry PDF album using ReportLab matching selected Visual Theme & Font
def generate_album_pdf(entries: list[dict], explorer_name: str, theme_name: str, font_name: str) -> bytes:
    buffer = io.BytesIO()
    theme = ALBUM_THEMES.get(theme_name, ALBUM_THEMES["Vintage Map"])
    font_cfg = GOOGLE_FONTS_MAP.get(font_name, GOOGLE_FONTS_MAP["Playfair Display"])

    bg_color = colors.HexColor(theme["bg"])
    card_bg = colors.HexColor(theme["card_bg"])
    border_color = colors.HexColor(theme["border"])
    accent_color = colors.HexColor(theme["accent"])
    text_color = colors.HexColor(theme["text"])
    subtext_color = colors.HexColor(theme["subtext"])
    badge_bg = colors.HexColor(theme["badge_bg"])
    badge_text = colors.HexColor(theme["badge_text"])

    # UI EDITING: Paint themed page background, border frame, and footer watermark on every PDF page
    def draw_themed_page(canvas_obj, doc_obj):
        canvas_obj.saveState()
        width, height = A4
        canvas_obj.setFillColor(bg_color)
        canvas_obj.rect(0, 0, width, height, fill=1, stroke=0)

        canvas_obj.setStrokeColor(border_color)
        canvas_obj.setLineWidth(2.5)
        if theme["border_style"] == "dashed":
            canvas_obj.setDash(6, 4)
        canvas_obj.rect(12 * mm, 12 * mm, width - 24 * mm, height - 24 * mm, fill=0, stroke=1)
        if theme["border_style"] == "double":
            canvas_obj.setLineWidth(0.8)
            canvas_obj.rect(14.5 * mm, 14.5 * mm, width - 29 * mm, height - 29 * mm, fill=0, stroke=1)

        canvas_obj.setDash()
        canvas_obj.setFont(font_cfg["pdf_font"], 8.5)
        canvas_obj.setFillColor(subtext_color)
        footer_txt = pdf_safe_text(
            f"Explorer Quest: Lyon Edition  |  {explorer_name}  |  Theme: {theme_name}  |  Page {doc_obj.page}"
        )
        canvas_obj.drawCentredString(width / 2.0, 7.5 * mm, footer_txt)
        canvas_obj.restoreState()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AlbumTitle",
        parent=styles["Title"],
        fontName=font_cfg["pdf_bold"],
        fontSize=22,
        leading=26,
        textColor=accent_color,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "AlbumSubtitle",
        parent=styles["Normal"],
        fontName=font_cfg["pdf_font"],
        fontSize=11,
        leading=14,
        textColor=subtext_color,
        spaceAfter=14,
    )
    spot_style = ParagraphStyle(
        "SpotTitle",
        parent=styles["Heading2"],
        fontName=font_cfg["pdf_bold"],
        fontSize=14,
        leading=18,
        textColor=accent_color,
        spaceAfter=2,
    )
    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontName=font_cfg["pdf_bold"],
        fontSize=9.5,
        leading=12,
        textColor=badge_text,
    )
    body_style = ParagraphStyle(
        "DiaryBody",
        parent=styles["Normal"],
        fontName=font_cfg["pdf_font"],
        fontSize=11,
        leading=16,
        textColor=text_color,
    )

    story = [
        Paragraph(pdf_safe_text("Carnet de Voyage : Explorer Quest — Lyon"), title_style),
        Paragraph(
            pdf_safe_text(
                f"Travel Photo Album of {explorer_name}  •  Style: {theme_name} ({font_name})  •  Generated {date.today().isoformat()}"
            ),
            subtitle_style,
        ),
    ]

    for idx, entry in enumerate(entries, start=1):
        card_flowables = []
        badge_table = Table(
            [[Paragraph(pdf_safe_text(f"#{idx}  |  {entry['entry_date']}  |  {entry['lyon_spot']}"), meta_style)]],
            colWidths=[160 * mm],
        )
        badge_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), badge_bg),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        card_flowables.append(badge_table)
        card_flowables.append(Spacer(1, 6))
        card_flowables.append(Paragraph(pdf_safe_text(entry["lyon_spot"]), spot_style))

        # LOGIC: Embed photo proportionally if present on disk
        img_path = entry.get("image_path") or ""
        if img_path and os.path.exists(img_path):
            try:
                with PILImage.open(img_path) as pil_im:
                    orig_w, orig_h = pil_im.size
                max_w = 148 * mm
                max_h = 85 * mm
                scale = min(max_w / float(orig_w), max_h / float(orig_h))
                rl_img = RLImage(img_path, width=orig_w * scale, height=orig_h * scale)
                card_flowables.append(Spacer(1, 4))
                card_flowables.append(rl_img)
                card_flowables.append(Spacer(1, 6))
            except Exception:
                pass

        safe_diary = pdf_safe_text(entry["diary_text"]).replace("\n", "<br/>")
        card_flowables.append(Paragraph(safe_diary, body_style))

        outer_card = Table([[card_flowables]], colWidths=[168 * mm])
        outer_card.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), card_bg),
                    ("BOX", (0, 0), (-1, -1), 1.2, border_color),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(outer_card)
        story.append(Spacer(1, 12))

    doc.build(story, onFirstPage=draw_themed_page, onLaterPages=draw_themed_page)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ==============================================================================
# 4. UI STYLING, GOOGLE FONTS INJECTION & BILINGUAL HEADER COMPONENTS
# ==============================================================================

# UI EDITING: Inject Google Fonts stylesheet and custom Lyon Burgundy & Gold architectural CSS
def inject_global_styles():
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=Cinzel:wght@400;700&family=Lobster&family=Montserrat:wght@400;600;700&family=Oswald:wght@400;600;700&family=Pacifico&family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Space+Grotesk:wght@400;600;700&family=Special+Elite&family=Syne:wght@500;700;800&display=swap" rel="stylesheet">
        <style>
            /* UI EDITING: Main app container and Lyon heritage color accents */
            .lyon-hero {
                background: linear-gradient(135deg, #4A0E1C 0%, #7A1C32 55%, #B8860B 100%);
                padding: 1.6rem 2rem;
                border-radius: 16px;
                color: #FFFDF9;
                border: 1px solid rgba(255, 215, 0, 0.35);
                box-shadow: 0 10px 28px rgba(74, 14, 28, 0.22);
                margin-bottom: 1.2rem;
            }
            .lyon-hero h1 {
                font-family: 'Cinzel', serif;
                font-size: 2.1rem;
                margin: 0;
                letter-spacing: 0.5px;
                color: #FFFDF9;
            }
            .lyon-hero .en-sub {
                font-family: 'Montserrat', sans-serif;
                font-size: 1.02rem;
                color: #FCE8B2;
                margin-top: 0.25rem;
                font-weight: 500;
            }
            .bilingual-section {
                border-left: 5px solid #8B1E3F;
                padding-left: 0.9rem;
                margin-top: 1.1rem;
                margin-bottom: 0.85rem;
            }
            .bilingual-section .fr-title {
                font-family: 'Playfair Display', serif;
                font-size: 1.45rem;
                font-weight: 700;
                margin: 0;
                line-height: 1.25;
            }
            .bilingual-section .en-subtitle {
                font-family: 'Montserrat', sans-serif;
                font-size: 0.9rem;
                opacity: 0.78;
                margin: 0.15rem 0 0 0;
                font-weight: 500;
            }
            .guide-card {
                border: 1px solid rgba(139, 30, 63, 0.25);
                border-radius: 14px;
                padding: 1.15rem 1.3rem;
                background: rgba(255, 250, 245, 0.04);
                margin-bottom: 0.9rem;
            }
            .guide-badge {
                display: inline-block;
                background: #8B1E3F;
                color: #FFF8EE;
                font-size: 0.72rem;
                font-weight: 700;
                padding: 0.2rem 0.6rem;
                border-radius: 999px;
                letter-spacing: 0.6px;
                margin-bottom: 0.45rem;
            }
            .riddle-card {
                border: 1px solid rgba(184, 134, 11, 0.4);
                border-radius: 14px;
                padding: 1.1rem 1.25rem;
                margin-bottom: 0.85rem;
                background: rgba(139, 30, 63, 0.04);
            }
            .coupon-card {
                border: 2px dashed #B8860B;
                border-radius: 14px;
                padding: 1.1rem 1.25rem;
                margin-bottom: 0.9rem;
                background: rgba(184, 134, 11, 0.06);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# UI EDITING: Reusable helper enforcing French primary header + English subtitle across every section
def render_bilingual_header(fr_title: str, en_subtitle: str, size: str = "1.42rem"):
    st.markdown(
        f"""
        <div class="bilingual-section">
            <div class="fr-title" style="font-size:{size};">{fr_title}</div>
            <div class="en-subtitle">{en_subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==============================================================================
# 5. MAIN APPLICATION INITIALIZATION & SIDEBAR EXPLORER PASSPORT
# ==============================================================================

# LOGIC: Initialize SQLite database and load persistent Explorer state on startup
init_db()
if "profile" not in st.session_state:
    st.session_state["profile"] = load_profile()
if "lyon_unlocked" not in st.session_state:
    st.session_state["lyon_unlocked"] = False
if "detected_location" not in st.session_state:
    st.session_state["detected_location"] = None

inject_global_styles()
profile = st.session_state["profile"]
tier_en, tier_fr = compute_explorer_tier(profile["total_points"])
available_points = max(0, profile["total_points"] - profile["spent_points"])

# UI EDITING: Sidebar Explorer Passport displaying persistent rank, points, and GPS status
with st.sidebar:
    render_bilingual_header("Passeport de l'Explorateur", "Explorer Passport & Progress", size="1.2rem")

    new_name = st.text_input(
        "Nom de l'Explorateur / Explorer Callsign",
        value=profile["explorer_name"],
        max_chars=32,
    )
    if new_name.strip() and new_name.strip() != profile["explorer_name"]:
        profile["explorer_name"] = new_name.strip()
        save_profile(profile)
        st.toast(f"Bienvenue, {profile['explorer_name']}! Profile saved.")

    st.markdown(f"**Rang / Rank:** `{tier_en}` (*{tier_fr}*)")
    col_p1, col_p2 = st.columns(2)
    col_p1.metric("Points Totaux", f"{profile['total_points']} pts")
    col_p2.metric("Solde Boutique", f"{available_points} pts")

    # LOGIC: Compute progress bar toward next Explorer rank threshold
    next_thresholds = [200, 500, 900, 1200]
    next_goal = next((t for t in next_thresholds if profile["total_points"] < t), 1200)
    progress_ratio = min(1.0, profile["total_points"] / float(next_goal))
    st.progress(progress_ratio, text=f"Next Rank Milestone: {profile['total_points']} / {next_goal} pts")

    st.markdown(
        f"- **Énigmes Résolues (Riddles):** `{len(profile['solved_riddles'])} / {len(LYON_RIDDLES)}`\n"
        f"- **Quêtes Photo (Photo Quests):** `{len(profile['completed_quests'])} / {len(LYON_PHOTO_QUESTS)}`\n"
        f"- **Coupons Obtenus (Vouchers):** `{len(profile['redeemed_coupons'])}`"
    )

    st.divider()
    render_bilingual_header("Statut GPS Lyon", "Lyon Geofence Status", size="1.05rem")
    if st.session_state["lyon_unlocked"]:
        st.success("Lyon Quests: UNLOCKED (Déverrouillé)")
    else:
        st.warning("Lyon Quests: LOCKED (Verify GPS in Location Hub)")

    # LOGIC: Optional remote testing toggle if Explorer is testing the app outside Lyon, France
    with st.expander("Mode Test à Distance / Remote Preview Toggle"):
        st.caption(
            "Real mobile GPS in the Location Hub automatically unlocks Lyon quests. "
            "Use this toggle only if testing from outside Lyon, France."
        )
        demo_unlock = st.checkbox(
            "Simuler la présence GPS à Lyon / Simulate Lyon GPS",
            value=st.session_state.get("demo_lyon_override", False),
        )
        st.session_state["demo_lyon_override"] = demo_unlock
        if demo_unlock:
            st.session_state["lyon_unlocked"] = True
        elif not (st.session_state.get("detected_location") or {}).get("is_lyon", False):
            st.session_state["lyon_unlocked"] = False


# ==============================================================================
# 6. HERO BANNER & BILINGUAL NAVIGATION TABS
# ==============================================================================

# UI EDITING: Main application hero banner with French primary headline and English subtitle
st.markdown(
    f"""
    <div class="lyon-hero">
        <h1>🦁 Explorer Quest : Édition Lyon — Capitale des Gaules</h1>
        <div class="en-sub">
            Explorer Quest: Lyon Edition • Welcome, <strong>{profile['explorer_name']}</strong>!
            Discover Lugdunum, solve 12 heritage riddles, craft your travel album, and unlock local rewards.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# UI EDITING: Four primary application hubs with French primary labels and English subtitles
tab_hub, tab_quests, tab_diary, tab_store = st.tabs(
    [
        "📍 Hub GPS & Guide Interactif (Location Hub)",
        "🧩 Énigmes & Quêtes (12 Riddles & Quests)",
        "📓 Journal & Studio Album PDF (Diary & PDF)",
        "🎟️ Boutique de Coupons (Coupon Store)",
    ]
)


# ==============================================================================
# TAB 1: LYON LOCATION HUB (GPS DETECTION + INTERACTIVE LYON GUIDE)
# ==============================================================================
with tab_hub:
    render_bilingual_header(
        "Détection GPS Mobile & Déverrouillage de Lyon",
        "Real-Time Mobile GPS Detection & Lyon Quest Geofence",
    )
    st.write(
        f"Tap the GPS beacon button below, **{profile['explorer_name']}**, so your mobile browser can "
        "transmit your live coordinates, detect your neighborhood and city via Nominatim, and verify if you are in Lyon, France."
    )

    # LOGIC: Render streamlit_geolocation component and reverse-geocode coordinates via Nominatim
    gps_col1, gps_col2 = st.columns([1, 2])
    with gps_col1:
        st.markdown("**Activer le Signal GPS / Activate GPS Beacon:**")
        location = streamlit_geolocation()

    if location and location.get("latitude") is not None and location.get("longitude") is not None:
        lat = float(location["latitude"])
        lon = float(location["longitude"])
        geo_info = reverse_geocode_location(lat, lon)
        st.session_state["detected_location"] = geo_info

        if geo_info["is_lyon"] or st.session_state.get("demo_lyon_override", False):
            st.session_state["lyon_unlocked"] = True

        # LOGIC: Mandatory success banner announcing Explorer's reverse-geocoded neighborhood/city/country
        st.success(
            f"Explorer, your mobile GPS confirms you are currently in {geo_info['formatted_place']}!"
        )

        if geo_info["is_lyon"]:
            st.info(
                f"🎉 Félicitations {profile['explorer_name']}! Your coordinates ({lat:.4f}, {lon:.4f}) "
                "confirm you are inside **Lyon, France** — all Lyon Real-Life Photo Quests are UNLOCKED!"
            )
        else:
            st.warning(
                f"🧭 Explorer, your GPS coordinates ({lat:.4f}, {lon:.4f}) place you outside **Lyon, France**. "
                "Travel to Lyon (or enable 'Simulate Lyon GPS' in the sidebar) to unlock field photo quests!"
            )

        # UI EDITING: Render Explorer's live GPS pin on interactive map
        map_df = pd.DataFrame([{"lat": lat, "lon": lon}])
        st.map(map_df, zoom=13)
    else:
        with gps_col2:
            st.info(
                f"📡 **En attente du signal GPS / Awaiting GPS Fix:** Click the location icon on the left, "
                f"**{profile['explorer_name']}**, and allow location permissions to pinpoint your live position on the map."
            )

    st.divider()
    render_bilingual_header(
        "Les Incontournables de Lyon : Guide Culturel & Historique",
        "Must-Visit Places in Lyon: History, Traboules, Architecture, Bouchons & Festivals",
    )

    # UI EDITING: Interactive category filter & rich guide cards
    selected_topic = st.selectbox(
        "Choisir un Thème Culturel / Select Cultural Guide Chapter:",
        options=["Tous les Thèmes / All Chapters"] + [f"{s['title_fr']} ({s['title_en']})" for s in LYON_GUIDE_SECTIONS],
    )

    for section in LYON_GUIDE_SECTIONS:
        full_label = f"{section['title_fr']} ({section['title_en']})"
        if selected_topic != "Tous les Thèmes / All Chapters" and selected_topic != full_label:
            continue
        highlights_html = "".join(f"<li>{item}</li>" for item in section["highlights"])
        st.markdown(
            f"""
            <div class="guide-card">
                <span class="guide-badge">{section['badge']}</span>
                <div style="font-family:'Playfair Display',serif; font-size:1.3rem; font-weight:700;">
                    {section['title_fr']}
                </div>
                <div style="font-family:'Montserrat',sans-serif; font-size:0.88rem; opacity:0.78; margin-bottom:0.6rem;">
                    {section['title_en']}
                </div>
                <p style="line-height:1.6; margin-bottom:0.6rem;">{section['summary']}</p>
                <ul style="margin:0; padding-left:1.2rem;">{highlights_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    render_bilingual_header(
        "Cartes Postales des Monuments Emblématiques",
        "Interactive Visual Photo Cards of Iconic Lyon Landmarks",
    )

    # UI EDITING: 3-column grid of iconic Lyon landmark visual photo cards
    card_cols = st.columns(3)
    for idx, landmark in enumerate(LYON_LANDMARK_CARDS):
        with card_cols[idx % 3]:
            with st.container(border=True):
                st.caption(f"📍 {landmark['district']}  •  {landmark['tag']}")
                try:
                    st.image(landmark["image_url"], use_container_width=True)
                except Exception:
                    st.markdown(f"🏛️ **{landmark['name_fr']}**")
                st.markdown(f"**{landmark['name_fr']}**")
                st.caption(f"*{landmark['name_en']}*")
                st.write(landmark["caption"])


# ==============================================================================
# TAB 2: 12 LYON RIDDLES & 3 REAL-LIFE PHOTO QUESTS
# ==============================================================================
with tab_quests:
    render_bilingual_header(
        "Les 12 Énigmes du Patrimoine Lyonnais (50 pts chacune)",
        "12 Curated Lyon Riddles & Trivia Challenges (50 Points Each)",
    )
    st.write(
        f"Solve all 12 authentic riddles about Lyon, **{profile['explorer_name']}**, to earn up to **600 points** "
        "and uncover historical secrets along the way."
    )

    # LOGIC: Render 12 curated Lyon riddles with hint expanders, answer validation, and SQLite persistence
    for idx, riddle in enumerate(LYON_RIDDLES, start=1):
        rid = riddle["id"]
        is_solved = rid in profile["solved_riddles"]
        status_icon = "✅ RÉSOLUE / SOLVED" if is_solved else "🔒 À DÉCOUVRIR / UNSOLVED (+50 pts)"

        with st.container(border=True):
            top_c1, top_c2 = st.columns([4, 1])
            with top_c1:
                st.markdown(f"**Énigme #{idx} : {riddle['topic_fr']}**")
                st.caption(f"*{riddle['topic_en']}*")
            with top_c2:
                st.markdown(f"**`{status_icon}`**")

            st.write(riddle["riddle"])

            with st.expander("💡 Indice de l'Explorateur / Need a Hint?"):
                st.info(riddle["hint"])

            if is_solved:
                st.success(f"🎉 Bravo {profile['explorer_name']}! **Fun Fact:** {riddle['fun_fact']}")
            else:
                ans_col, btn_col = st.columns([3, 1])
                with ans_col:
                    user_guess = st.text_input(
                        f"Votre réponse / Your Answer (#{idx})",
                        key=f"input_{rid}",
                        placeholder="Type your answer here...",
                        label_visibility="collapsed",
                    )
                with btn_col:
                    submitted = st.button("Valider / Submit", key=f"btn_{rid}", use_container_width=True)

                if submitted:
                    if check_riddle_answer(user_guess, riddle["accepted_answers"]):
                        profile["solved_riddles"].append(rid)
                        profile["total_points"] += riddle["points"]
                        save_profile(profile)
                        st.balloons()
                        st.success(
                            f"🏆 Magnifique, {profile['explorer_name']}! +50 Points earned! "
                            f"**Fun Fact:** {riddle['fun_fact']}"
                        )
                        st.rerun()
                    else:
                        st.error(
                            f"Pas tout à fait, {profile['explorer_name']}! Check the hint above and try again."
                        )

    st.divider()
    render_bilingual_header(
        "Quêtes Photo sur le Terrain à Lyon (200 pts chacune)",
        "3 Real-Life Field Photo Quests in Lyon (200 Points Each)",
    )

    # LOGIC: Check whether Lyon GPS geofence is unlocked before allowing field photo quest submissions
    if not st.session_state["lyon_unlocked"]:
        st.warning(
            f"🔐 **Quêtes Verrouillées / Field Quests Locked:** {profile['explorer_name']}, verify your live GPS "
            "coordinates inside **Lyon, France** in the **Location Hub** (or activate Remote Test Toggle in the sidebar) "
            "to unlock these 200-point field photo quests!"
        )

    for quest in LYON_PHOTO_QUESTS:
        qid = quest["id"]
        q_done = qid in profile["completed_quests"]

        with st.container(border=True):
            qc1, qc2 = st.columns([4, 1])
            with qc1:
                st.markdown(f"### {quest['title_fr']}")
                st.caption(f"*{quest['title_en']}*  •  📍 **{quest['location_tag']}**")
            with qc2:
                st.markdown("**`✅ COMPLÉTÉE`**" if q_done else "**`📸 +200 PTS`**")

            st.write(quest["instructions"])

            if q_done:
                st.success(
                    f"🏅 Mission Accomplished, {profile['explorer_name']}! You earned **200 pts** for this Lyon field quest."
                )
            else:
                q_photo = st.file_uploader(
                    f"Télécharger la Photo Preuve / Upload Field Proof ({quest['location_tag']})",
                    type=["jpg", "jpeg", "png"],
                    key=f"upload_{qid}",
                    disabled=not st.session_state["lyon_unlocked"],
                )
                q_note = st.text_input(
                    "Note de terrain / Field GPS Log Note",
                    key=f"note_{qid}",
                    placeholder="e.g., Spotted the spiral staircase inside 54 Rue Saint-Jean!",
                    disabled=not st.session_state["lyon_unlocked"],
                )
                if st.button(
                    "Valider la Quête Photo (+200 pts) / Complete Photo Quest",
                    key=f"complete_{qid}",
                    disabled=not st.session_state["lyon_unlocked"],
                ):
                    if q_photo is None:
                        st.error(
                            f"Explorer {profile['explorer_name']}, please upload your field photograph first!"
                        )
                    else:
                        saved_img = persist_uploaded_image(q_photo, prefix=qid)
                        profile["completed_quests"].append(qid)
                        profile["total_points"] += quest["points"]
                        save_profile(profile)
                        # LOGIC: Also log completed field quest directly into Explorer's travel diary
                        add_diary_entry(
                            entry_date=date.today().isoformat(),
                            lyon_spot=quest["location_tag"],
                            diary_text=q_note.strip() or f"Completed {quest['title_en']} in Lyon!",
                            image_path=saved_img,
                            theme="Vintage Map",
                            font="Playfair Display",
                        )
                        st.balloons()
                        st.success(
                            f"🎉 Incroyable, {profile['explorer_name']}! +200 Points awarded and saved to your Travel Diary!"
                        )
                        st.rerun()


# ==============================================================================
# TAB 3: EXPLORER DIARY, ALBUM STUDIO & REPORTLAB PDF EXPORT
# ==============================================================================
with tab_diary:
    render_bilingual_header(
        "Journal de Voyage & Studio de Création d'Album",
        "Explorer Travel Diary, Visual Theme Studio & PDF Album Export",
    )

    studio_col1, studio_col2 = st.columns([1.15, 1])

    with studio_col1:
        render_bilingual_header(
            "Nouvelle Page de Journal",
            "Write & Save a Dated Lyon Diary Entry",
            size="1.15rem",
        )
        with st.form("diary_entry_form", clear_on_submit=True):
            entry_date = st.date_input("Date du Souvenir / Entry Date", value=date.today())
            lyon_spot = st.selectbox(
                "Lieu Emblématique / Lyon Landmark Tag",
                options=[
                    "Vieux Lyon & Les Traboules",
                    "Basilique Notre-Dame de Fourvière",
                    "La Croix-Rousse & Mur des Canuts",
                    "Place Bellecour & Presqu'île",
                    "Parc de la Tête d'Or",
                    "Musée des Confluences",
                    "Les Halles de Lyon Paul Bocuse",
                    "Place des Terreaux & Opéra",
                    "Théâtres Romains de Fourvière",
                    "Autre Lieu Secret à Lyon",
                ],
            )
            diary_text = st.text_area(
                "Récit de l'Explorateur / Travel Diary Story",
                height=130,
                placeholder="Describe the aromas of a Bouchon, a hidden Renaissance courtyard, or sunset over the Saône...",
            )
            diary_photo = st.file_uploader(
                "Photographie Souvenir / Upload Travel Photo",
                type=["jpg", "jpeg", "png"],
            )
            save_entry_btn = st.form_submit_button("💾 Enregistrer dans l'Album / Save to SQLite Diary")

            if save_entry_btn:
                if not diary_text.strip():
                    st.error(f"Explorer {profile['explorer_name']}, please write a short travel note before saving!")
                else:
                    saved_path = persist_uploaded_image(diary_photo, prefix="diary")
                    default_theme = st.session_state.get("selected_album_theme", "Vintage Map")
                    default_font = st.session_state.get("selected_album_font", "Playfair Display")
                    add_diary_entry(
                        entry_date=entry_date.isoformat(),
                        lyon_spot=lyon_spot,
                        diary_text=diary_text.strip(),
                        image_path=saved_path,
                        theme=default_theme,
                        font=default_font,
                    )
                    st.success(f"✨ Souvenir enregistré, {profile['explorer_name']}! Saved to your Lyon Album.")
                    st.rerun()

    with studio_col2:
        render_bilingual_header(
            "Personnalisation & Export PDF",
            "10 Album Visual Themes, 10 Google Fonts & PDF Export Engine",
            size="1.15rem",
        )
        # UI EDITING: Select from the 10 Album Visual Themes and 10 Custom Google Fonts
        selected_theme = st.selectbox(
            "Thème Visuel de l'Album / Album Visual Theme (10 Styles)",
            options=list(ALBUM_THEMES.keys()),
            key="selected_album_theme",
        )
        selected_font = st.selectbox(
            "Typographie Personnalisée / Custom Google Font (10 Fonts)",
            options=list(GOOGLE_FONTS_MAP.keys()),
            key="selected_album_font",
        )

        theme_cfg = ALBUM_THEMES[selected_theme]
        font_css = GOOGLE_FONTS_MAP[selected_font]["css"]

        # UI EDITING: Live interactive theme & font preview card
        st.markdown(
            f"""
            <div style="
                background:{theme_cfg['bg']};
                border: 3px {theme_cfg['border_style']} {theme_cfg['border']};
                border-radius: 14px;
                padding: 1.1rem;
                margin-top: 0.4rem;
                margin-bottom: 0.8rem;
            ">
                <div style="
                    background:{theme_cfg['card_bg']};
                    border: 1px solid {theme_cfg['border']};
                    border-radius: 10px;
                    padding: 0.9rem;
                ">
                    <span style="
                        background:{theme_cfg['badge_bg']};
                        color:{theme_cfg['badge_text']};
                        font-family:{font_css};
                        font-size:0.75rem;
                        padding:0.2rem 0.55rem;
                        border-radius:6px;
                        font-weight:700;
                    ">APERÇU EN DIRECT • LIVE PREVIEW</span>
                    <h4 style="
                        font-family:{font_css};
                        color:{theme_cfg['accent']};
                        margin:0.55rem 0 0.2rem 0;
                        font-size:1.25rem;
                    ">{selected_theme} — {selected_font}</h4>
                    <p style="
                        font-family:{font_css};
                        color:{theme_cfg['text']};
                        font-size:0.95rem;
                        margin:0;
                        line-height:1.5;
                    ">
                        “Under the golden lights of Fourvière, {profile['explorer_name']} uncovered a hidden
                        traboule echoing with centuries of Lyonnais silk history.”
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # LOGIC: Generate formatted ReportLab PDF album from all saved SQLite diary entries
        saved_entries = load_diary_entries()
        if saved_entries:
            pdf_data = generate_album_pdf(
                entries=saved_entries,
                explorer_name=profile["explorer_name"],
                theme_name=selected_theme,
                font_name=selected_font,
            )
            st.download_button(
                label=f"📥 Télécharger l'Album PDF ({selected_theme}) / Download PDF Album",
                data=pdf_data,
                file_name=f"Explorer_Quest_Lyon_{selected_theme.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.info("Add at least one diary entry on the left to enable PDF Album Export!")

    st.divider()
    render_bilingual_header(
        "Aperçu de Votre Album Photo de Lyon",
        "Live Styled Gallery of Your Saved Lyon Diary Entries",
    )

    saved_entries = load_diary_entries()
    if not saved_entries:
        st.info(
            f"Votre carnet est encore vierge, **{profile['explorer_name']}**. Create your first Lyon memory above!"
        )
    else:
        t_cfg = ALBUM_THEMES[selected_theme]
        f_css = GOOGLE_FONTS_MAP[selected_font]["css"]
        for entry in saved_entries:
            st.markdown(
                f"""
                <div style="
                    background:{t_cfg['bg']};
                    border: 3px {t_cfg['border_style']} {t_cfg['border']};
                    border-radius: 16px;
                    padding: 1.2rem;
                    margin-bottom: 1rem;
                ">
                    <div style="
                        background:{t_cfg['card_bg']};
                        border: 1px solid {t_cfg['border']};
                        border-radius: 12px;
                        padding: 1rem 1.2rem;
                    ">
                        <span style="
                            background:{t_cfg['badge_bg']};
                            color:{t_cfg['badge_text']};
                            font-family:{f_css};
                            font-size:0.78rem;
                            padding:0.22rem 0.65rem;
                            border-radius:6px;
                            font-weight:700;
                        ">📅 {entry['entry_date']}  •  📍 {entry['lyon_spot']}</span>
                        <h3 style="
                            font-family:{f_css};
                            color:{t_cfg['accent']};
                            margin:0.6rem 0 0.4rem 0;
                        ">{entry['lyon_spot']}</h3>
                        <p style="
                            font-family:{f_css};
                            color:{t_cfg['text']};
                            font-size:1.02rem;
                            line-height:1.65;
                            margin-bottom:0.4rem;
                        ">{entry['diary_text']}</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            img_col, del_col = st.columns([4, 1])
            with img_col:
                if entry.get("image_path") and os.path.exists(entry["image_path"]):
                    st.image(entry["image_path"], width=360, caption=f"{entry['lyon_spot']} ({entry['entry_date']})")
            with del_col:
                if st.button("🗑️ Supprimer / Delete", key=f"del_entry_{entry['id']}"):
                    delete_diary_entry(entry["id"])
                    st.rerun()


# ==============================================================================
# TAB 4: REAL-WORLD COUPON STORE & REDEEMED VOUCHER WALLET
# ==============================================================================
with tab_store:
    render_bilingual_header(
        "Boutique de Coupons & Privilèges Locaux",
        "Real-World Reward Store: Redeem Points at Lyon Bouchons, Shops & Hotels",
    )

    available_points = max(0, profile["total_points"] - profile["spent_points"])
    st.info(
        f"💰 **Solde Disponible / Available Points Balance:** **{available_points} pts** "
        f"(Total Earned: {profile['total_points']} pts | Redeemed: {profile['spent_points']} pts)"
    )

    store_cols = st.columns(2)
    for idx, cpn in enumerate(COUPON_CATALOG):
        with store_cols[idx % 2]:
            st.markdown(
                f"""
                <div class="coupon-card">
                    <span class="guide-badge">{cpn['category']} • {cpn['cost']} PTS</span>
                    <div style="font-family:'Playfair Display',serif; font-size:1.2rem; font-weight:700; margin-top:0.2rem;">
                        {cpn['title_fr']}
                    </div>
                    <div style="font-family:'Montserrat',sans-serif; font-size:0.86rem; opacity:0.8; margin-bottom:0.45rem;">
                        {cpn['title_en']}
                    </div>
                    <div style="font-weight:600; margin-bottom:0.25rem;">🏪 {cpn['merchant']}</div>
                    <div style="font-size:0.88rem; opacity:0.85;">{cpn['details']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            can_afford = available_points >= cpn["cost"]
            if st.button(
                f"Échanger ({cpn['cost']} pts) / Redeem Voucher",
                key=f"redeem_{cpn['id']}",
                disabled=not can_afford,
                use_container_width=True,
            ):
                voucher_code = f"LYON-{uuid.uuid4().hex[:6].upper()}"
                profile["spent_points"] += cpn["cost"]
                profile["redeemed_coupons"].append(
                    {
                        "code": voucher_code,
                        "merchant": cpn["merchant"],
                        "title_fr": cpn["title_fr"],
                        "title_en": cpn["title_en"],
                        "cost": cpn["cost"],
                        "redeemed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    }
                )
                save_profile(profile)
                st.balloons()
                st.success(
                    f"🎟️ Félicitations {profile['explorer_name']}! Voucher **{voucher_code}** unlocked for {cpn['merchant']}!"
                )
                st.rerun()

    st.divider()
    render_bilingual_header(
        "Portefeuille de Vos Coupons Actifs",
        "Your Redeemed Lyon Vouchers Wallet",
    )

    if not profile["redeemed_coupons"]:
        st.caption(
            f"No vouchers redeemed yet, {profile['explorer_name']}. Solve riddles or complete photo quests to earn points!"
        )
    else:
        for v in reversed(profile["redeemed_coupons"]):
            with st.container(border=True):
                vc1, vc2 = st.columns([3, 1])
                with vc1:
                    st.markdown(f"**{v['title_fr']}** — *{v['title_en']}*")
                    st.caption(f"🏪 {v['merchant']}  •  Redeemed on {v['redeemed_at']} ({v['cost']} pts)")
                with vc2:
                    st.code(v["code"], language=None)