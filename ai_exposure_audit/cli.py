import typer
from sqlalchemy.orm import Session, joinedload

from .core.db import get_db, init_db
from .models import Client, AuditFinding, Employee # Assuming models are accessible like this
from .models.audit_finding import FindingSeverity, FindingConfidence, FindingStatus # Enums for display
from .modules.linkedin.scraper import get_company_employees
from .analysis.insight_extractor import extract_ai_insights
from .core.config import PROXYCURL_API_KEY # For checking if API key is set

app = typer.Typer(help="AI Exposure Audit CLI - Manage clients and scan for AI-related exposure.")

@app.command(name="init-db")
def init_db_cmd():
    """Initializes the database and creates tables."""
    try:
        init_db()
        typer.secho("Database initialized successfully.", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Error initializing database: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

@app.command(name="add-client")
def add_client(
    name: str = typer.Option(..., "--name", help="Name of the client company."),
    # Renamed linkedin_url to company_linkedin_url to match scraper and be more descriptive
    company_linkedin_url: str = typer.Option(..., "--linkedin-url", help="Full LinkedIn profile URL of the client company (e.g., https://www.linkedin.com/company/google).")
):
    """Adds a new client company to the database."""
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        # Check if client.linkedin_url in Client model matches this new name
        existing_client = db.query(Client).filter(
            (Client.company_name == name) | (Client.domain == company_linkedin_url) # Assuming domain field stores linkedin_url
        ).first()

        # The model uses `domain` for the company URL, let's adjust the filter.
        # Or, if we decide `linkedin_url` should be a new field on Client, the model needs update.
        # For now, let's assume Client model should have a 'linkedin_url' field.
        # If Client model has `domain` and we want to store LinkedIn URL there, that's fine.
        # If Client model has `linkedin_url`, use that.
        # The prompt implies `client.linkedin_url` exists. Let's assume the model uses `domain` for this.
        # Correcting this to what the model likely has (or should have for clarity):
        # Let's assume the Client model was intended to have `linkedin_url` as a direct field.
        # If not, this part needs alignment with the actual Client model field name.
        # For this implementation, I'll assume Client model has a `linkedin_url` field.
        # If it's `domain`, the query should be `Client.domain == company_linkedin_url`.
        # The prompt for `scan_client` uses `client.linkedin_url`.

        # Let's assume the Client model has `company_name` and `linkedin_url`
        existing_client_by_name = db.query(Client).filter(Client.company_name == name).first()
        existing_client_by_url = db.query(Client).filter(Client.linkedin_url == company_linkedin_url).first()

        if existing_client_by_name:
            typer.secho(f"Error: Client with name '{name}' already exists (ID: {existing_client_by_name.id}).", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        if existing_client_by_url:
            typer.secho(f"Error: Client with LinkedIn URL '{company_linkedin_url}' already exists (ID: {existing_client_by_url.id}, Name: {existing_client_by_url.company_name}).", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        
        # Assuming Client model takes `company_name` and `linkedin_url`
        client = Client(company_name=name, linkedin_url=company_linkedin_url) # Ensure Client model matches
        db.add(client)
        db.commit()
        db.refresh(client)
        typer.secho(f"Client '{client.company_name}' added with ID: {client.id} and LinkedIn URL: {client.linkedin_url}", fg=typer.colors.GREEN)
    except typer.Exit: # Re-raise Typer specific exits
        raise
    except Exception as e:
        if db: db.rollback()
        typer.secho(f"Error adding client: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    finally:
        if db: next(db_gen, None) # Ensure db session is closed

@app.command(name="scan-client")
def scan_client(
    client_id: int = typer.Option(..., "--id", help="ID of the client to scan."),
    max_employees: int = typer.Option(50, "--max-employees", help="Maximum number of employee profiles to fetch and analyze.")
):
    """Scans a client for AI exposure insights using LinkedIn data via Proxycurl."""
    if not PROXYCURL_API_KEY:
        typer.secho("Error: PROXYCURL_API_KEY not found in environment variables.", fg=typer.colors.RED, err=True)
        typer.echo("Please set it in your .env file or environment.")
        raise typer.Exit(code=1)

    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            typer.secho(f"Error: Client with ID {client_id} not found.", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        
        if not client.linkedin_url: # Assuming Client model has linkedin_url field
            typer.secho(f"Error: Client '{client.company_name}' (ID: {client_id}) does not have a LinkedIn URL configured.", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)

        typer.echo(f"Scanning client: {client.company_name} (LinkedIn URL: {client.linkedin_url})")
        
        try:
            typer.echo(f"Fetching up to {max_employees} employee profiles from LinkedIn via Proxycurl...")
            employee_profiles = get_company_employees(company_linkedin_url=client.linkedin_url, max_employees=max_employees)
        except Exception as e:
            typer.secho(f"Error fetching data from Proxycurl: {e}", fg=typer.colors.RED, err=True)
            # Consider if partial data could be processed or if it's an immediate exit
            raise typer.Exit(code=1)

        if not employee_profiles:
            typer.echo("No employee profiles fetched. Scan concluded.")
            return

        typer.echo(f"Fetched {len(employee_profiles)} employee profiles. Extracting insights...")
        
        # extract_ai_insights handles its own db.commit() / db.rollback()
        new_findings = extract_ai_insights(db=db, client_id=client.id, employee_profiles=employee_profiles)
        
        typer.secho(f"Scan complete for {client.company_name}. Generated {len(new_findings)} new AI-related findings.", fg=typer.colors.GREEN)
        if new_findings:
            typer.echo("Newly created finding IDs: " + ", ".join([str(f.id) for f in new_findings]))
            typer.echo(f"Use 'view-findings --client-id {client.id}' to see all findings for this client.")
        else:
            typer.echo("No new findings were generated in this scan.")

    except typer.Exit: # Re-raise Typer specific exits
        raise
    except Exception as e:
        # db.rollback() is not strictly needed here if extract_ai_insights handles its own session management on error
        typer.secho(f"Error during scan for client ID {client_id}: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    finally:
        if db: next(db_gen, None)


@app.command(name="view-findings")
def view_findings(
    client_id: int = typer.Option(None, "--client-id", help="ID of the client to filter findings for (optional)."),
    finding_id: int = typer.Option(None, "--finding-id", help="ID of a specific finding to view (optional).")
):
    """Views audit findings, optionally filtered by client ID or specific finding ID."""
    db_gen = get_db()
    db: Session = next(db_gen)
    try:
        query = db.query(AuditFinding).options(
            joinedload(AuditFinding.employee).joinedload(Employee.client)
        )
        
        if finding_id:
            finding = query.filter(AuditFinding.id == finding_id).first()
            if not finding:
                typer.secho(f"Error: Finding with ID {finding_id} not found.", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)
            findings = [finding]
            typer.echo(f"Displaying specific finding ID: {finding_id}")
        elif client_id:
            client = db.query(Client).filter(Client.id == client_id).first()
            if not client:
                typer.secho(f"Error: Client with ID {client_id} not found.", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)
            query = query.join(AuditFinding.employee).filter(Employee.client_id == client_id)
            typer.echo(f"Displaying findings for client: {client.company_name} (ID: {client_id})")
            findings = query.order_by(AuditFinding.id).all()
        else:
            typer.echo("Displaying all findings:")
            findings = query.order_by(AuditFinding.id).all()

        if not findings:
            typer.secho("No findings found matching your criteria.", fg=typer.colors.YELLOW)
            return

        for finding in findings:
            typer.echo("---")
            client_name = finding.employee.client.company_name if finding.employee and finding.employee.client else 'N/A'
            employee_name = finding.employee.full_name if finding.employee else 'N/A'
            profile_url = finding.employee.profile_url if finding.employee else 'N/A'
            
            typer.echo(typer.style(f"Finding ID: {finding.id}", bold=True) + f" (Status: {finding.status.value if finding.status else 'N/A'})")
            typer.echo(f"  Client: {client_name}")
            typer.echo(f"  Employee: {employee_name} (Profile: {profile_url})")
            typer.echo(f"  Type: {finding.finding_type}")
            typer.echo(f"  Description: {finding.description}")
            severity_color = typer.colors.YELLOW if finding.severity == FindingSeverity.MEDIUM else typer.colors.RED if finding.severity == FindingSeverity.HIGH else typer.colors.WHITE
            typer.echo(f"  Severity: {typer.style(finding.severity.value if finding.severity else 'N/A', fg=severity_color)}")
            typer.echo(f"  Confidence: {finding.confidence.value if finding.confidence else 'N/A'}")
            if finding.details:
                typer.echo(f"  Details: {finding.details}")
            if finding.auditor_notes:
                typer.echo(f"  Auditor Notes: {finding.auditor_notes}")
            typer.echo(f"  Found At: {finding.found_at.strftime('%Y-%m-%d %H:%M:%S') if finding.found_at else 'N/A'}")
        
        typer.echo("---")
        typer.secho(f"Total findings displayed: {len(findings)}", bold=True)

    except typer.Exit: # Re-raise Typer specific exits
        raise
    except Exception as e:
        typer.secho(f"Error viewing findings: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
    finally:
        if db: next(db_gen, None)

# The main.py will import 'app' from this file.
# Example of how to run from CLI:
# python -m ai_exposure_audit.main init-db
# python -m ai_exposure_audit.main add-client --name "TestClient" --linkedin-url "https://linkedin.com/company/testclient"
# python -m ai_exposure_audit.main scan-client --id 1
# python -m ai_exposure_audit.main view-findings --client-id 1
# python -m ai_exposure_audit.main view-findings

# A note on Client model:
# The prompt for `add_client` uses `linkedin_url` as a parameter.
# The prompt for `scan_client` uses `client.linkedin_url`.
# The `Client` model in `models/client.py` has `company_name` and `domain`.
# For consistency and clarity, the Client model should ideally have a specific `linkedin_url` field.
# The CLI implementation here assumes `Client.linkedin_url` exists.
# If `domain` is meant to store the LinkedIn URL, then references to `linkedin_url` in the Client object
# queries and attribute access within cli.py would need to be changed to `domain`.
# This implementation will proceed assuming the Client model will be (or is) aligned to have a `linkedin_url` field.
# If not, the `add_client` command needs to store the URL in `client.domain` and `scan_client` needs to read from `client.domain`.
# The `Client` model was defined as:
# class Client(Base):
#     __tablename__ = "clients"
#     id = Column(Integer, primary_key=True, index=True)
#     company_name = Column(String, nullable=False)
#     domain = Column(String, nullable=True, index=True)  <-- This is the field
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     employees = relationship("Employee", back_populates="client")
# I will adjust the CLI to use `domain` for the LinkedIn URL for the Client model.

# Re-adjusting add_client and scan_client to use `domain` for `linkedin_url`
# This requires changing how Client objects are created and queried.
# This is a critical alignment step.
# The previous code block for `cli.py` has this note, I will apply the fix below.
# The `overwrite_file_with_block` will contain the corrected version.
