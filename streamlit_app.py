import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time as dtime
import pytz
from astral import LocationInfo
from astral.sun import sun
import ephem
import swisseph as swe

# -- Core Sequences and Dictionaries --
bird_emojis = {'Crow':'🐦','Cock':'🐓','Peacock':'🦚','Vulture':'🦅','Owl':'🦉'}
activity_emoji = {'Ruling':'👑','Eating':'🍽️','Walking':'🚶','Sleeping':'💤','Dying':'💀'}
activity_color = {'Ruling':'#388e3c','Eating':'#43a047','Walking':'#fbc02d','Sleeping':'#757575','Dying':'#c62828'}
plus_map = {'very good': '++++++++', 'good': '++++++', 'average': '++++', 'bad': '++', 'very bad': '+'}

# Bird sequences and activity orders per your rules
bird_sequences = {
    ('Shukla', 'Day'):    ['Vulture','Owl','Crow','Cock','Peacock'],
    ('Shukla', 'Night'):  ['Vulture','Peacock','Cock','Crow','Owl'],
    ('Krishna','Day'):    ['Vulture','Crow','Peacock','Owl','Cock'],
    ('Krishna','Night'):  ['Vulture','Cock','Owl','Peacock','Crow'],
}
activity_orders = {
    ('Shukla','Day'):    [('Eating',30),('Walking',36),('Ruling',48),('Sleeping',18),('Dying',12)],
    ('Shukla','Night'):  [('Eating',30),('Ruling',48),('Dying',12),('Walking',36),('Sleeping',18)],
    ('Krishna','Day'):   [('Eating',30),('Dying',12),('Sleeping',18),('Ruling',48),('Walking',36)],
    ('Krishna','Night'): [('Eating',30),('Sleeping',18),('Walking',36),('Dying',12),('Ruling',48)],
}
# Ruling/Death Days
ruling_days_table = {
    'Shukla': {
        'Day': {'Sunday': 'Vulture', 'Monday': 'Owl', 'Tuesday': 'Vulture', 'Wednesday': 'Owl', 'Thursday': 'Crow', 'Friday': 'Cock', 'Saturday': 'Peacock'},
        'Night': {'Sunday': 'Crow', 'Monday': 'Cock', 'Tuesday': 'Crow', 'Wednesday': 'Crow', 'Thursday': 'Peacock', 'Friday': 'Vulture', 'Saturday': 'Owl'}
    },
    'Krishna': {
        'Day': {'Sunday': 'Cock', 'Monday': 'Peacock', 'Tuesday': 'Cock', 'Wednesday': 'Crow', 'Thursday': 'Owl', 'Friday': 'Vulture', 'Saturday': 'Peacock'},
        'Night': {'Sunday': 'Vulture', 'Monday': 'Vulture', 'Tuesday': 'Crow', 'Wednesday': 'Crow', 'Thursday': 'Crow', 'Friday': 'Peacock', 'Saturday': 'Cock'}
    }
}
death_days_table = {
    'Shukla': {
        'Day': {'Sunday': 'Owl', 'Monday': 'Crow', 'Tuesday': 'Cock', 'Wednesday': 'Peacock', 'Thursday': 'Vulture', 'Friday': 'Owl', 'Saturday': 'Vulture'},
        'Night': {'Sunday': 'Owl', 'Monday': 'Crow', 'Tuesday': 'Cock', 'Wednesday': 'Peacock', 'Thursday': 'Owl', 'Friday': 'Owl', 'Saturday': 'Vulture'}
    },
    'Krishna': {
        'Day': {'Sunday': 'Crow', 'Monday': 'Owl', 'Tuesday': 'Owl', 'Wednesday': 'Vulture', 'Thursday': 'Crow', 'Friday': 'Peacock', 'Saturday': 'Cock'},
        'Night': {'Sunday': 'Crow', 'Monday': 'Owl', 'Tuesday': 'Owl', 'Wednesday': 'Vulture', 'Thursday': 'Crow', 'Friday': 'Peacock', 'Saturday': 'Cock'}
    }
}
day_rating = {
    'Peacock': {'Walking': 'good', 'Ruling': 'average', 'Sleeping': 'bad', 'Dying': 'average', 'Eating': 'good'},
    'Vulture': {'Walking': 'average', 'Ruling': 'very good', 'Sleeping': 'bad', 'Dying': 'very bad', 'Eating': 'good'},
    'Owl': {'Walking': 'good', 'Ruling': 'good', 'Sleeping': 'average', 'Dying': 'bad', 'Eating': 'average'},
    'Crow': {'Walking': 'very bad', 'Ruling': 'good', 'Sleeping': 'very bad', 'Dying': 'very bad', 'Eating': 'bad'},
    'Cock': {'Walking': 'very bad', 'Ruling': 'very bad', 'Sleeping': 'bad', 'Dying': 'very bad', 'Eating': 'good'},
}
night_rating = {
    'Peacock': {'Walking': 'bad', 'Ruling': 'very good', 'Sleeping': 'average', 'Dying': 'average', 'Eating': 'average'},
    'Vulture': {'Walking': 'average', 'Ruling': 'very good', 'Sleeping': 'bad', 'Dying': 'very bad', 'Eating': 'good'},
    'Owl': {'Walking': 'average', 'Ruling': 'average', 'Sleeping': 'average', 'Dying': 'bad', 'Eating': 'very good'},
    'Crow': {'Walking': 'average', 'Ruling': 'average', 'Sleeping': 'average', 'Dying': 'very bad', 'Eating': 'very bad'},
    'Cock': {'Walking': 'average', 'Ruling': 'average', 'Sleeping': 'very bad', 'Dying': 'very bad', 'Eating': 'average'},
}
friends = {
    'Shukla': {
        'Vulture': ['Peacock','Owl'],
        'Owl': ['Vulture','Crow'],
        'Crow': ['Owl','Cock'],
        'Cock': ['Crow','Peacock'],
        'Peacock': ['Cock','Vulture'],
    },
    'Krishna': {
        'Vulture': ['Crow','Peacock'],
        'Owl': ['Crow','Cock'],
        'Crow': ['Vulture','Owl'],
        'Cock': ['Crow','Peacock'],
        'Peacock': ['Cock','Vulture'],
    }
}
enemies = {
    'Shukla': {
        'Vulture': ['Crow','Cock'],
        'Owl': ['Cock','Peacock'],
        'Crow': ['Peacock','Vulture'],
        'Cock': ['Vulture','Owl'],
        'Peacock': ['Owl','Crow'],
    },
    'Krishna': {
        'Vulture': ['Owl','Cock'],
        'Owl': ['Vulture','Peacock'],
        'Crow': ['Cock','Peacock'],
        'Cock': ['Vulture','Owl'],
        'Peacock': ['Owl','Crow'],
    }
}

def get_paksha_swisseph(date):
    LAT, LON = 19.0760, 72.8777
    TIMEZONE = 5.5
    dt = datetime(date.year, date.month, date.day, 12, 0, 0)
    jd = swe.julday(dt.year, dt.month, dt.day, dt.hour - TIMEZONE)
    sun_long = swe.calc_ut(jd, swe.SUN)[0][0]
    moon_long = swe.calc_ut(jd, swe.MOON)[0][0]
    diff = (moon_long - sun_long) % 360
    return 'Shukla' if diff <= 180 else 'Krishna'

def periods_by_durations(start, durations):
    period_starts = [start]
    for d in durations[:-1]:
        period_starts.append(period_starts[-1] + timedelta(minutes=d))
    periods = [(period_starts[i], period_starts[i+1]) for i in range(len(durations)-1)]
    periods.append((period_starts[-1], period_starts[-1]+timedelta(minutes=durations[-1])))
    return periods

def rotate(lst, n):
    n = n % len(lst)
    return lst[n:] + lst[:n]

def get_relation(main_bird, sub_bird, paksha):
    if sub_bird == main_bird:
        return 'Self'
    elif sub_bird in friends[paksha][main_bird]:
        return 'Friend'
    elif sub_bird in enemies[paksha][main_bird]:
        return 'Enemy'
    else:
        return 'Neutral'

# --------- UI ---------
st.markdown("<h1 style='text-align:center;color:#3e2723'>Pancha Pakshi – Five Bird Shastra</h1>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    date_selected = st.date_input("Date", datetime.now().date())
with col2:
    time_selected = st.time_input("Time (local Mumbai)", dtime(hour=12, minute=0))

tz = pytz.timezone("Asia/Kolkata")
dt_full = datetime.combine(date_selected, time_selected)
dt_full = tz.localize(dt_full)
city = LocationInfo("Mumbai", "India", "Asia/Kolkata", 19.0760, 72.8777)
sun_times = sun(city.observer, date=date_selected, tzinfo=tz)
sunrise, sunset = sun_times['sunrise'], sun_times['sunset']
next_sunrise = sun(city.observer, date=date_selected+timedelta(days=1), tzinfo=tz)['sunrise']

paksha = get_paksha_swisseph(date_selected)
weekday = date_selected.strftime("%A")
sun_icon = "☀️"
moon_icon = "🌙"
cloud_icon = "☁️" if paksha == 'Shukla' else "🌑"

ruling_bird_day = ruling_days_table[paksha]['Day'][weekday]
dying_bird_day  = death_days_table[paksha]['Day'][weekday]
ruling_bird_night = ruling_days_table[paksha]['Night'][weekday]
dying_bird_night  = death_days_table[paksha]['Night'][weekday]

st.markdown(f"<b>Paksha:</b> <span style='font-size:20px;color:#388e3c'>{paksha} Paksha</span>", unsafe_allow_html=True)
st.markdown(
    f"""
    <div style='font-size:19px;margin-bottom:8px'>
      {sun_icon} <b>Day:</b> Ruling Bird {bird_emojis[ruling_bird_day]} <b>{ruling_bird_day}</b> &nbsp; Dying Bird {bird_emojis[dying_bird_day]} <b>{dying_bird_day}</b><br>
      {moon_icon} <b>Night:</b> Ruling Bird {bird_emojis[ruling_bird_night]} <b>{ruling_bird_night}</b> &nbsp; Dying Bird {bird_emojis[dying_bird_night]} <b>{dying_bird_night}</b>
    </div>
    """, unsafe_allow_html=True
)
st.markdown(f"<b>Sunrise:</b> {sunrise.strftime('%I:%M %p')} &nbsp; <b>Sunset:</b> {sunset.strftime('%I:%M %p')}", unsafe_allow_html=True)

# --- DAYTIME ---
base_seq_day = bird_sequences[(paksha, 'Day')]
seq_start_day = base_seq_day.index(ruling_bird_day)
yama_bird_order_day = rotate(base_seq_day, seq_start_day)

activity_order_day = activity_orders[(paksha, 'Day')]
act_names_day = [a[0] for a in activity_order_day]
act_durations_day = [a[1] for a in activity_order_day]
day_periods = periods_by_durations(sunrise, [sum(act_durations_day)]*5)
for yama_idx, (main_start, main_end) in enumerate(day_periods):
    main_bird = yama_bird_order_day[yama_idx % 5]
    activity = act_names_day[yama_idx % 5]
    color = activity_color[activity]
    emoji = activity_emoji[activity]
    is_current = main_start <= dt_full < main_end
    border = "4px solid #d84315" if is_current else "2px solid #eee"
    ausp = day_rating[main_bird][activity]
    rating = plus_map[ausp]
    st.markdown(
        f"""
        <div style='
            display:flex;
            align-items:center;
            background:{color}10;
            border-radius:18px;
            margin-bottom:8px;
            border:{border};
            padding: 14px 18px; 
            min-height:70px;'>
            <span style='font-size:21px;margin-right:10px;'>{sun_icon}</span>
            <span style='font-size:21px;margin-right:10px;'>{cloud_icon}</span>
            <span style='font-size:30px;margin-right:10px;'>{bird_emojis[ruling_bird_day]}</span>
            <span style='font-size:30px;margin-right:10px;'>{bird_emojis[dying_bird_day]}</span>
            <div style='font-size:38px;margin-right:18px;'>{bird_emojis[main_bird]}</div>
            <div style='flex:1;'>
                <span style='font-size:22px;font-weight:bold'>{main_bird}</span>
                <span style='margin-left:22px;font-size:38px'>{emoji}</span>
                <span style='margin-left:22px;font-size:22px;'><b>{activity}</b></span>
                <span style='margin-left:22px;font-size:17px;color:#333'>{main_start.strftime('%I:%M %p')} – {main_end.strftime('%I:%M %p')}</span>
                <span style='margin-left:22px;font-size:17px;color:#388e3c'><b>{ausp}</b></span>
                <span style='margin-left:12px;font-size:17px;'>{rating}</span>
            </div>
        </div>
        """, unsafe_allow_html=True
    )
    # Sub-periods (apahara)
    with st.expander("Show Sub-periods", expanded=is_current):
        sub_bird_order = rotate(yama_bird_order_day, yama_idx % 5)
        sub_activity_order = rotate(act_names_day, yama_idx % 5)
        sub_durations = rotate(act_durations_day, yama_idx % 5)
        sub_periods = periods_by_durations(main_start, sub_durations)
        sub_rows = []
        for j, (sstart, send) in enumerate(sub_periods):
            sbird = sub_bird_order[j]
            sact = sub_activity_order[j]
            sausp = day_rating[sbird][sact]
            srating = plus_map[sausp]
            relation = get_relation(main_bird, sbird, paksha)
            sub_rows.append({
                "Sub Bird": f"{bird_emojis[sbird]} {sbird}",
                "Activity": f"{activity_emoji[sact]} {sact}",
                "Relation": relation,
                "Auspiciousness": sausp,
                "Start": sstart.strftime("%I:%M %p"),
                "End": send.strftime("%I:%M %p"),
                "Rating": srating
            })
        st.dataframe(pd.DataFrame(sub_rows), hide_index=True, use_container_width=True)

# --- NIGHTTIME ---
base_seq_night = bird_sequences[(paksha, 'Night')]
seq_start_night = base_seq_night.index(ruling_bird_night)
yama_bird_order_night = rotate(base_seq_night, seq_start_night)

activity_order_night = activity_orders[(paksha, 'Night')]
act_names_night = [a[0] for a in activity_order_night]
act_durations_night = [a[1] for a in activity_order_night]
night_periods = periods_by_durations(sunset, [sum(act_durations_night)]*5)
for yama_idx, (main_start, main_end) in enumerate(night_periods):
    main_bird = yama_bird_order_night[yama_idx % 5]
    activity = act_names_night[yama_idx % 5]
    color = activity_color[activity]
    emoji = activity_emoji[activity]
    is_current = main_start <= dt_full < main_end
    border = "4px solid #d84315" if is_current else "2px solid #eee"
    ausp = night_rating[main_bird][activity]
    rating = plus_map[ausp]
    st.markdown(
        f"""
        <div style='
            display:flex;
            align-items:center;
            background:{color}10;
            border-radius:18px;
            margin-bottom:8px;
            border:{border};
            padding: 14px 18px; 
            min-height:70px;'>
            <span style='font-size:21px;margin-right:10px;'>{moon_icon}</span>
            <span style='font-size:21px;margin-right:10px;'>{cloud_icon}</span>
            <span style='font-size:30px;margin-right:10px;'>{bird_emojis[ruling_bird_night]}</span>
            <span style='font-size:30px;margin-right:10px;'>{bird_emojis[dying_bird_night]}</span>
            <div style='font-size:38px;margin-right:18px;'>{bird_emojis[main_bird]}</div>
            <div style='flex:1;'>
                <span style='font-size:22px;font-weight:bold'>{main_bird}</span>
                <span style='margin-left:22px;font-size:38px'>{emoji}</span>
                <span style='margin-left:22px;font-size:22px;'><b>{activity}</b></span>
                <span style='margin-left:22px;font-size:17px;color:#333'>{main_start.strftime('%I:%M %p')} – {main_end.strftime('%I:%M %p')}</span>
                <span style='margin-left:22px;font-size:17px;color:#388e3c'><b>{ausp}</b></span>
                <span style='margin-left:12px;font-size:17px;'>{rating}</span>
            </div>
        </div>
        """, unsafe_allow_html=True
    )
    with st.expander("Show Sub-periods", expanded=is_current):
        sub_bird_order = rotate(yama_bird_order_night, yama_idx % 5)
        sub_activity_order = rotate(act_names_night, yama_idx % 5)
        sub_durations = rotate(act_durations_night, yama_idx % 5)
        sub_periods = periods_by_durations(main_start, sub_durations)
        sub_rows = []
        for j, (sstart, send) in enumerate(sub_periods):
            sbird = sub_bird_order[j]
            sact = sub_activity_order[j]
            sausp = night_rating[sbird][sact]
            srating = plus_map[sausp]
            relation = get_relation(main_bird, sbird, paksha)
            sub_rows.append({
                "Sub Bird": f"{bird_emojis[sbird]} {sbird}",
                "Activity": f"{activity_emoji[sact]} {sact}",
                "Relation": relation,
                "Auspiciousness": sausp,
                "Start": sstart.strftime("%I:%M %p"),
                "End": send.strftime("%I:%M %p"),
                "Rating": srating
            })
        st.dataframe(pd.DataFrame(sub_rows), hide_index=True, use_container_width=True)

st.caption("Yama sequence begins from ruling bird for the mode, period logic and relationships match classical Pancha Pakshi rules and Drik style.")
