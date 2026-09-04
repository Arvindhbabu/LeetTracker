# LeetTracker

> A full-stack class analytics platform for tracking, analyzing, and visualizing students' LeetCode progress.

LeetTracker is a web-based analytics platform designed to help students, mentors, and educators monitor coding progress across a class.

It automatically synchronizes students' LeetCode statistics, maintains historical snapshots, calculates daily problem-solving growth, and presents the data through an interactive analytics dashboard.

---

## ✨ Features

### 📊 Class Overview

- View the complete class roster
- Track Easy, Medium, and Hard problems solved
- View total problems solved by each student
- Monitor student tracking status
- Identify students with pending LeetCode usernames

### 📈 Daily Progress Tracking

- Maintain cumulative daily snapshots
- Calculate verified daily problem-solving growth
- Track Easy, Medium, and Hard problem growth separately
- Handle missing historical snapshots safely
- Preserve historical progress instead of overwriting previous data

### 🏆 Leaderboard

- Rank students based on total problems solved
- Sort by:
  - Total solved
  - Hard solved
  - Daily growth
- Automatically assign ranks to students with valid data
- Keep students without configured usernames separate

### 📅 Historical Analytics

- Browse historical snapshots
- Compare student progress across dates
- View cumulative problem-solving statistics
- Analyze historical daily growth

### 🔄 Automatic Synchronization

- Automatically synchronize student statistics
- Background synchronization without requiring the dashboard to remain open
- Configurable synchronization interval
- Manual synchronization support
- Sync status monitoring
- Failed/pending student handling

### 🏅 LeetCode Achievements

- Display LeetCode badges
- Track student achievement information
- Present achievement data alongside coding progress

---

## 🏗️ Architecture

LeetTracker follows a modular full-stack architecture:

```text
┌─────────────────────────────┐
│          Frontend           │
│     Analytics Dashboard     │
└──────────────┬──────────────┘
               │
               │ HTTP / REST API
               ▼
┌─────────────────────────────┐
│           FastAPI           │
│        Backend API          │
├─────────────────────────────┤
│ Routes / API Layer          │
│ Sync Service                │
│ Automatic Sync Scheduler    │
│ Analytics / Progress Logic  │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│          Database           │
│   Student & Snapshot Data   │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│        LeetCode Data        │
│     Student Statistics      │
└─────────────────────────────┘
