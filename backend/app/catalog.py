"""Hardcoded tech entry-level job catalog the user can browse and apply to.
Kept as plain data so the demo always has something to score against."""
from __future__ import annotations

from .models import CatalogJob

CATALOG: list[CatalogJob] = [
    CatalogJob(
        id="cat-1",
        title="Junior Data Analyst",
        company="Northwind Labs",
        location="Paris (Hybrid)",
        tags=["SQL", "Python", "Dashboards", "Entry-level"],
        description=(
            "We're hiring a Junior Data Analyst to support our product and growth "
            "teams. You'll write SQL to pull data, build dashboards in Tableau or "
            "Looker, and run analyses that inform decisions. We expect comfort with "
            "Python (pandas), strong Excel/Sheets, and clear communication of "
            "findings to non-technical stakeholders. No prior full-time experience "
            "required — internships and academic projects count."
        ),
    ),
    CatalogJob(
        id="cat-2",
        title="Software Engineer I (Backend)",
        company="Cloudpeak",
        location="Remote (EU)",
        tags=["Python", "APIs", "SQL", "Git", "Entry-level"],
        description=(
            "Entry-level backend engineer to build and maintain REST APIs in Python "
            "(FastAPI/Django). You'll work with PostgreSQL, write unit tests, and "
            "ship features with code review. We look for solid fundamentals in data "
            "structures, familiarity with Git, and eagerness to learn. Bonus: Docker, "
            "cloud (AWS/GCP), and any open-source or side projects."
        ),
    ),
    CatalogJob(
        id="cat-3",
        title="Associate Product Manager",
        company="Brightside",
        location="London (Hybrid)",
        tags=["Product", "Analytics", "Stakeholders", "Entry-level"],
        description=(
            "APM role for early-career candidates. You'll help define requirements, "
            "analyze usage data, run user interviews, and coordinate engineering and "
            "design. Strong analytical skills (SQL or spreadsheets), clear written "
            "communication, and structured thinking are key. Experience leading a "
            "project or team — even academic — is a plus."
        ),
    ),
    CatalogJob(
        id="cat-4",
        title="Junior Machine Learning Engineer",
        company="Vellum AI",
        location="Berlin (On-site)",
        tags=["Python", "ML", "PyTorch", "Data", "Entry-level"],
        description=(
            "Join our ML team to build and evaluate models. You'll preprocess data "
            "with pandas/NumPy, train models in PyTorch or scikit-learn, and help put "
            "them into production. We want strong Python, an understanding of core ML "
            "concepts, and good data intuition. Coursework, Kaggle, or research "
            "projects are welcome in lieu of industry experience."
        ),
    ),
    CatalogJob(
        id="cat-5",
        title="Business Intelligence Analyst (Graduate)",
        company="Meridian Retail",
        location="Amsterdam (Hybrid)",
        tags=["SQL", "Tableau", "Reporting", "Entry-level"],
        description=(
            "Graduate BI Analyst to own reporting for our commercial teams. Build and "
            "maintain dashboards, write performant SQL, and translate business "
            "questions into data answers. Detail-oriented, comfortable with large "
            "datasets, and able to present insights clearly. Financial modeling or "
            "market research exposure is a plus."
        ),
    ),
    CatalogJob(
        id="cat-6",
        title="Frontend Developer (Junior)",
        company="Pixel & Co",
        location="Remote (Global)",
        tags=["React", "JavaScript", "CSS", "Entry-level"],
        description=(
            "Junior frontend developer to build responsive UIs in React. You'll turn "
            "designs into clean, accessible components, work with REST APIs, and "
            "collaborate in code review. We want solid JavaScript, HTML/CSS, and some "
            "React; a portfolio or projects matters more than years of experience."
        ),
    ),
]

_BY_ID = {c.id: c for c in CATALOG}


def get_catalog_job(cat_id: str) -> CatalogJob | None:
    return _BY_ID.get(cat_id)
