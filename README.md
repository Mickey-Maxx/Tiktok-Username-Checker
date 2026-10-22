# TikTok Username Checker 🎵

A lightweight, multi-threaded desktop GUI application designed to check TikTok username availability, organize results, and help you confirm available names directly in the TikTok app.

> ⚠️ **Disclaimer & Notice**  
> *"Looks free"* is not a strict guarantee. TikTok has no official availability API; this tool checks public profile endpoints. Names that are banned, reserved, or recently deleted may appear free in the checker but cannot be claimed. **The final check must always be done inside the official TikTok app** (`Profile > Edit profile > Username`).

---

## ⚡ Features

* **Multiple Generation Sources**:
  * **Random**: Generate random letter combinations (optional numbers/underscores).
  * **Word-like**: Generate pronounceable, brandable names (e.g., *zoriv*, *kelmo*, *vanto*).
  * **Pattern Matching**: Custom syntax like `ak??`, `nova#`, or `??_x` (`?` = letter, `#` = number, `*` = either).
  * **Word Lists & Combination**: Import names or combine two word lists (e.g., `nova` + `fox` = `novafox`).
  * **Smart Variations**: Try prefixes/suffixes, letter doubling, dropping, or swapping.
* **Smart Suggestions**: Right-click any taken name to generate sound-alike spellings, brand tweaks, or minor variations.
* **Adaptive Rate Limiting (Auto-Pace)**: Automatically speeds up when TikTok is responsive and slows down when rate limits are detected.
* **Saved Sessions & Resume**: Pause or stop mid-run and resume remaining checks later without losing progress.
* **Built-in Review & Deduplication**: Filter results, track confirmed checkmarks vs. red errors, and re-check saved lists with one click.
* **30-Day Memory**: Automatically remembers taken names to avoid wasting requests in subsequent runs.

---

## 🚀 Download & Installation

Since pre-compiled binaries are provided for every major platform, you **do not** need Python or any command-line tools installed.

1. Go to the **[Releases](../../releases)** page on GitHub.
2. Download the package for your operating system:
   * **Windows**: `TikTokUserChecker-Windows.zip` (or `.exe`)
   * **macOS**: `TikTokUserChecker-macOS.zip`
   * **Linux**: `TikTokUserChecker-Linux.zip`
3. Extract the ZIP archive into its own folder.
4. Launch the application!

*(Note: On Windows or macOS, you may see a security warning like "Unidentified Developer" or "SmartScreen" on startup because the binary is self-compiled and unsigned. This is normal—click **More Info > Run Anyway** or **Open Anyway**).*

---

## 🖥️ How to Use

### 1. Check Tab
* Choose your name source (**Random**, **Word-like**, **Pattern**, **Word list**, **Combine**, or **Variations**).
* Set optional filters (*Must contain*, *Starts with*, *Ends with*).
* Adjust speed parameters (**Max names**, **Workers** (1–8), and **Delay**).
* Click **Start**. Use **Stop** at any time; your remaining names will be saved so you can click **Resume** later.

### 2. Results Tab
* View a live, color-coded table of checked names.
* Filter by status (*Available*, *Taken*, *Blocked*, *Other*).
* Right-click any row to trigger **Smart Suggestions** for similar name ideas.
* Export your visible rows to CSV.

### 3. Review Tab
* **Left Column (Available)**: Review names flagged as free. Type them in the TikTok app (without saving), then click **Checkmark** ($Y$) or **Red Error** ($N$).
* **Right Column (Confirmed)**: Keep a list of names you successfully claimed or verified.
* Click **Re-check these names first** to quickly verify that available names haven't been taken by someone else in the meantime.

---

## 📁 Local Saved Files

The application maintains several `.txt` and `.json` files in its directory to store your state locally:

| File | Purpose |
| :--- | :--- |
| `available_usernames.txt` | Names waiting to be tested inside the TikTok app |
| `confirmed_usernames.txt` | Names you've verified with a checkmark in the app |
| `rejected_usernames.txt` | Names refused by the app |
| `taken_usernames.txt` | Taken names (skipped automatically for 30 days) |
| `pending_usernames.txt` | Remaining queue from stopped or interrupted runs |
| `tiktok_checker_settings.json` | Saved application settings |

*Delete any file if you wish to clear or reset that specific history.*

---

## 📏 TikTok Username Rules

* Length must be **2 to 24 characters**.
* Allowed characters: **Letters, numbers, underscores (`_`), and periods (`.`)**.
* Usernames **cannot end with a period**.
* *Tip*: Very short names (2–3 characters) almost always fail inside the app even if they appear free. Names with 5+ characters yield much higher success rates.

---

## 💡 Best Practices & Rate Limits

* If TikTok begins blocking requests, the app will pause and slow down automatically.
* If a run stops due to rate limiting, **wait a few minutes** before clicking **Resume**, and consider reducing the worker count or increasing the minimum delay.
* TikTok enforces a strict limit allowing users to change their username only **once every 30 days**.
