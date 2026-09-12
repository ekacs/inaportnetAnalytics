# Walkthrough — Composite Fraud Risk Screening Index (CFRSI) Integration

The project has been updated based on the research paper [`Inaportnet-update.pdf`](file:///d:/Documents/inaportnetAnalytics/papers/Inaportnet-update.pdf) (*Wijaya & Setyawan, 2026*). All code, scripts, modules, dashboard pages, and documentation have been committed to the new Git branch: **`main-v3-composite-fraud`**.

---

## 🛠️ Summary of Changes

### 1. Git Repository & Branching

- Created and checked out new branch **`main-v3-composite-fraud`**.
- Committed all changes (`git commit -m "feat: implement CFRSI composite fraud risk screening engine (Wijaya & Setyawan 2026)"`).

### 2. Standalone Research Script

- **[`scripts/05_fraud_risk_analysis.py`](file:///d:/Documents/inaportnetAnalytics/scripts/05_fraud_risk_analysis.py)**:
  - Implements Rule-Based Anomaly Detection (5 Red Flag criteria).
  - Fits OLS Regression & computes Modified Z-Score residuals ($Z \le -2.5$).
  - Trains Isolation Forest model (`contamination=0.07`, `random_state=42`).
  - Aggregates sub-indices into **Composite Fraud Risk Screening Index (CFRSI)** with Min-Max scaling `[0.10, 1.00]`.
  - Performs 5-Tier Risk Classification (Percentile vs Fixed-Scale).

### 3. Dashboard Core Modules & Requirements

- **[`inaportnetDashboard/requirements.txt`](file:///d:/Documents/inaportnetAnalytics/inaportnetDashboard/requirements.txt)**: Added `scikit-learn` and `statsmodels`.
- **[`inaportnetDashboard/modules/analysis.py`](file:///d:/Documents/inaportnetAnalytics/inaportnetDashboard/modules/analysis.py)**: Added `compute_fraud_risk_analysis()` and `get_fraud_national_summary()`.
- **[`inaportnetDashboard/modules/visualization.py`](file:///d:/Documents/inaportnetAnalytics/inaportnetDashboard/modules/visualization.py)**: Added Plotly visualization functions:
  - `plot_volume_vs_red_flag_percentage()` (Recreates Figure 2 in paper)
  - `plot_red_flag_breakdown()` (Donut chart of 5 Red Flag rules)
  - `plot_cfrsi_port_ranking()` (Recreates Table 9 ranking)
  - `plot_subindices_breakdown()` (Grouped bar chart comparing Rule, Stat, ML sub-indices)
  - `plot_risk_category_distribution()` (Recreates Table 10 comparing Percentile vs Fixed Scale)

### 4. Interactive Streamlit Page & Navigation

- **[`inaportnetDashboard/pages/6_🛡️_Fraud_Risk_Screening.py`](file:///d:/Documents/inaportnetAnalytics/inaportnetDashboard/pages/6_%F0%9F%9B%A1%EF%B8%8F_Fraud_Risk_Screening.py)**:
  - New dedicated dashboard page for CFRSI & Anti-Fraud Governance.
  - KPI Cards for Total PKK, Red Flag %, Stat Outliers, ML Anomalies, and High-Risk Ports.
  - 4 Interactive Tabs:
    - **Tab 1: Composite Risk Index (CFRSI)**: Port rankings, sub-indices comparison, interactive table with risk tier filters.
    - **Tab 2: Rule-Based Red Flags**: Breakdown of 5 rules (Quick approval, Long duration, Low oversight 00-04, GT manipulation, Same vessel <2h).
    - **Tab 3: Statistical & ML Anomalies**: OLS residual distribution & Modified Z-Score outliers ($Z \le -2.5$) alongside Isolation Forest multidimensional anomaly scores.
    - **Tab 4: Anti-Fraud Governance & Risk Tiers**: Percentile vs Fixed-scale 5-Tier classification, OJK 4-Pillar Anti-Fraud Strategy guidelines, Escalation Matrix.
- **[`inaportnetDashboard/app.py`](file:///d:/Documents/inaportnetAnalytics/inaportnetDashboard/app.py)**: Updated sidebar navigation links and navigation grid cards to include the Fraud Risk Screening page.

### 5. Documentation

- **[`workflow.md`](file:///d:/Documents/inaportnetAnalytics/workflow.md)**: Updated Mermaid flowchart and stage documentation to incorporate the 4th Analytics Engine (Fraud Risk Screening Engine & CFRSI).
- **[`README.md`](file:///d:/Documents/inaportnetAnalytics/README.md)**: Added documentation for the CFRSI engine, 5 Red Flag rules, paper citation (*Wijaya & Setyawan, 2026*), and new page functionality.

---

## 🧪 Verification Results

1. **Standalone Script Execution**:
   - Command: `python scripts/05_fraud_risk_analysis.py`
   - Result: Executed clean (Exit code 0). Correctly computed CFRSI scores, sub-indices, and 5-tier risk levels.
2. **Dashboard Module Import Verification**:
   - Command: `python -c "import sys; sys.path.insert(0, 'inaportnetDashboard'); import modules.analysis as a; import modules.visualization as v; print('ALL MODULES LOADED OK')"`
   - Result: `ALL MODULES LOADED OK` (Exit code 0).
3. **Git Status & Branch Verification**:
   - Active branch: `main-v3-composite-fraud`
   - Working tree: Clean (`nothing to commit, working tree clean`).
