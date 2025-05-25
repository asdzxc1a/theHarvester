import logging
from sqlalchemy.orm import Session
from sqlalchemy.sql import func # for now()

from ..core.config import AI_JOB_TITLE_KEYWORDS
from ..core.db import Base # Required if we manipulate tables directly, not strictly for session usage
from ..models import Employee, AuditFinding, FindingSeverity, FindingConfidence, FindingStatus

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_ai_insights(db: Session, client_id: int, employee_profiles: list[dict]) -> list[AuditFinding]:
    """
    Processes employee data, identifies AI-related job titles, and creates 
    Employee and AuditFinding records in the database.

    Args:
        db (Session): SQLAlchemy Session object.
        client_id (int): The ID of the client company these employees belong to.
        employee_profiles (list[dict]): A list of dictionaries, where each dictionary 
                                         contains employee data from the scraper 
                                         (e.g., {'profile_url': '...', 'full_name': '...', 'job_title': '...'}).

    Returns:
        list[AuditFinding]: A list of newly created AuditFinding objects.
    """
    new_findings = []
    processed_employees_count = 0
    new_employees_count = 0
    updated_employees_count = 0

    if not AI_JOB_TITLE_KEYWORDS:
        logger.warning("AI_JOB_TITLE_KEYWORDS is empty. No AI-related job titles will be identified.")
        # Decide if this should be a critical error or just a warning. For now, warning.

    for profile_data in employee_profiles:
        processed_employees_count += 1
        profile_url = profile_data.get('profile_url')
        full_name = profile_data.get('full_name', 'N/A')
        job_title = profile_data.get('job_title', 'N/A') # This is 'headline' from Proxycurl

        if not profile_url:
            logger.warning(f"Skipping profile due to missing 'profile_url': {profile_data}")
            continue

        # Get or Create Employee
        employee = db.query(Employee).filter_by(profile_url=profile_url, client_id=client_id).first()

        if employee:
            # Employee exists, check for updates
            updated = False
            if employee.job_title != job_title:
                employee.job_title = job_title
                updated = True
            if employee.full_name != full_name and full_name != 'N/A': # Only update if new name is not N/A
                employee.full_name = full_name
                updated = True
            
            employee.raw_data = profile_data # Always update raw_data
            employee.last_scraped_at = func.now() # Update last_scraped_at timestamp
            
            if updated:
                updated_employees_count +=1
                logger.info(f"Updating existing employee: {employee.full_name} (ID: {employee.id}), URL: {profile_url}")
            db.add(employee) # Add to session to mark for update
        else:
            # Employee does not exist, create new
            new_employees_count += 1
            employee = Employee(
                client_id=client_id,
                profile_url=profile_url,
                full_name=full_name,
                job_title=job_title,
                raw_data=profile_data, # Store the original scraped info
                last_scraped_at=func.now()
            )
            db.add(employee)
            logger.info(f"Creating new employee: {employee.full_name}, URL: {profile_url}")
        
        # Flush to get employee.id if it's a new record or to ensure updates are staged
        # It's generally better to flush once before the commit, or let commit handle it,
        # but if employee.id is needed immediately (which it is for AuditFinding), flushing is necessary.
        try:
            db.flush() 
        except Exception as e:
            logger.error(f"Error flushing session for employee {profile_url}: {e}")
            db.rollback() # Rollback changes for this employee if flush fails
            continue # Skip to next profile

        if not employee.id:
            logger.error(f"Employee ID not available after flush for {profile_url}. Skipping finding creation.")
            continue

        # Analyze Job Title for AI keywords
        if not job_title or job_title == 'N/A':
            logger.debug(f"Skipping AI keyword analysis for employee {employee.id} due to missing job title.")
            continue

        for keyword in AI_JOB_TITLE_KEYWORDS:
            if keyword.lower() in job_title.lower():
                description = f"Job title/headline '{job_title}' contains AI-related keyword: '{keyword}'."
                
                # Check for Duplicate Finding for this specific employee, type, and description
                existing_finding = db.query(AuditFinding).filter_by(
                    employee_id=employee.id,
                    finding_type="AI_related_job_title",
                    description=description # Match description to avoid re-adding if re-processed with same job title
                ).first()

                if existing_finding:
                    logger.debug(f"Duplicate AI-related job title finding already exists for employee {employee.id} with keyword '{keyword}'. Skipping.")
                    # Optionally, update existing_finding.last_seen_at or similar if needed
                else:
                    new_finding = AuditFinding(
                        employee_id=employee.id,
                        finding_type="AI_related_job_title",
                        description=description,
                        severity=FindingSeverity.MEDIUM, # Default for now
                        confidence=FindingConfidence.HIGH, # Default for now
                        status=FindingStatus.PENDING,
                        details={"matched_keyword": keyword, "job_title": job_title} # Store as JSON
                    )
                    new_findings.append(new_finding)
                    db.add(new_finding)
                    logger.info(f"New AI-related job title finding for employee {employee.id} (Job: '{job_title}', Keyword: '{keyword}')")
                    db.flush() # Flush to get finding ID if needed elsewhere, or simply add to session
                
                break # One finding per employee for this type is enough for MVP

    try:
        db.commit()
        logger.info(f"Committed changes to the database.")
        logger.info(f"Processed {processed_employees_count} profiles.")
        logger.info(f"Created {new_employees_count} new employees, updated {updated_employees_count} existing employees.")
        logger.info(f"Created {len(new_findings)} new AI-related job title audit findings.")
    except Exception as e:
        logger.error(f"Error committing session: {e}")
        db.rollback()
        # Depending on policy, might want to re-raise or handle differently
        raise # Re-raise the exception after rollback

    return new_findings

# Example usage (for conceptual understanding, not for direct execution here)
# if __name__ == '__main__':
#     from ..core.db import SessionLocal, init_db
#     init_db() # Ensure tables are created
#     db_session = SessionLocal()
# 
#     # 1. Create a dummy client
#     from ..models.client import Client
#     dummy_client = Client(company_name="TestCorp Inc.", domain="testcorp.com")
#     db_session.add(dummy_client)
#     db_session.commit()
#     client_id_for_test = dummy_client.id
#     print(f"Created dummy client with ID: {client_id_for_test}")
# 
#     # 2. Sample employee profiles (simulating scraper output)
#     sample_profiles = [
#         {'profile_url': 'linkedin.com/in/johndoe-ai', 'full_name': 'John Doe', 'job_title': 'Lead AI Researcher'},
#         {'profile_url': 'linkedin.com/in/janesmith-ml', 'full_name': 'Jane Smith', 'job_title': 'Machine Learning Engineer'},
#         {'profile_url': 'linkedin.com/in/peterjones-dev', 'full_name': 'Peter Jones', 'job_title': 'Software Developer'},
#         {'profile_url': 'linkedin.com/in/johndoe-ai', 'full_name': 'John A. Doe', 'job_title': 'Director of AI Research'}, # Update
#         {'profile_url': 'linkedin.com/in/emptyjob', 'full_name': 'Empty Job', 'job_title': None},
#     ]
# 
#     # 3. Run the extraction
#     print(f"\nRunning AI insight extraction for client ID: {client_id_for_test}...")
#     created_findings = extract_ai_insights(db_session, client_id_for_test, sample_profiles)
# 
#     print(f"\nExtraction complete. {len(created_findings)} new findings created:")
#     for finding in created_findings:
#         print(f"  - Finding ID: {finding.id}, Employee ID: {finding.employee_id}, Desc: {finding.description}")
# 
#     # 4. Verify data (optional manual check)
#     all_employees = db_session.query(Employee).filter_by(client_id=client_id_for_test).all()
#     print(f"\nTotal employees for client {client_id_for_test} in DB: {len(all_employees)}")
#     for emp in all_employees:
#         print(f"  - Emp ID: {emp.id}, Name: {emp.full_name}, Title: {emp.job_title}, URL: {emp.profile_url}, Last Scraped: {emp.last_scraped_at}")
#         for find in emp.audit_findings:
#             print(f"    - Finding: {find.description} (Severity: {find.severity.value})")
# 
#     db_session.close()
