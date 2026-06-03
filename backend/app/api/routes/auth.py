from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.security import RoleName, create_access_token, get_password_hash, verify_password
from app.models import Role, User, UserRole
from app.schemas.auth import TokenResponse, UserLogin, UserRegister
from app.schemas.common import DevTokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/dev-token", response_model=DevTokenResponse)
def issue_dev_token() -> DevTokenResponse:
    """Return a short-lived JWT for the built-in dev analyst account.

    Only available when APP_ENV=development.
    """
    settings = get_settings()
    if settings.app_env != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    token = create_access_token(
        subject="00000000-0000-0000-0000-000000000001",
        email="dev-analyst@example.com",
        roles={RoleName.admin, RoleName.analyst},
        settings=settings,
    )
    return DevTokenResponse(access_token=token, token_type="bearer")


@router.post("/register", response_model=TokenResponse)
def register(
    request: UserRegister,
    db: Session = Depends(get_db_session),
) -> TokenResponse:
    """Register a new user, automatically seeding default roles if missing,
    assigning the analyst and admin roles to the user, and returning a JWT token.
    """
    settings = get_settings()
    
    # Check if email is already taken
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered.",
        )

    # 1. Create default roles if they do not exist
    admin_role = db.query(Role).filter(Role.name == RoleName.admin.value).first()
    if not admin_role:
        admin_role = Role(name=RoleName.admin.value, description="Administrator with full access")
        db.add(admin_role)
        
    analyst_role = db.query(Role).filter(Role.name == RoleName.analyst.value).first()
    if not analyst_role:
        analyst_role = Role(name=RoleName.analyst.value, description="Analyst with scan and read access")
        db.add(analyst_role)
        
    db.flush()  # Generate IDs

    # 2. Hash password and save new User
    hashed_pwd = get_password_hash(request.password)
    new_user = User(
        email=request.email,
        password_hash=hashed_pwd,
        display_name=request.display_name,
        is_active=True,
    )
    db.add(new_user)
    db.flush()

    # 3. Map user to roles (analyst and admin)
    user_admin_role = UserRole(user_id=new_user.id, role_id=admin_role.id)
    user_analyst_role = UserRole(user_id=new_user.id, role_id=analyst_role.id)
    db.add(user_admin_role)
    db.add(user_analyst_role)
    
    db.commit()
    db.refresh(new_user)

    # 4. Generate JWT Token
    roles = {RoleName.admin, RoleName.analyst}
    token = create_access_token(
        subject=str(new_user.id),
        email=new_user.email,
        roles=roles,
        settings=settings,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        email=new_user.email,
        display_name=new_user.display_name,
        roles=[role.value for role in roles],
    )


@router.post("/login", response_model=TokenResponse)
def login(
    request: UserLogin,
    db: Session = Depends(get_db_session),
) -> TokenResponse:
    """Authenticate email and password, returning a JWT token with user context and roles."""
    settings = get_settings()

    user = db.query(User).filter(User.email == request.email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # If the user was seeded (dev user) without a password hash, let them log in if they specify empty/any,
    # but for real accounts verify the hashed password.
    if user.password_hash is not None:
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
    else:
        # Dev user seeded with NULL password_hash. Ensure we only allow NULL/empty password check in development.
        if settings.app_env != "development" or request.password != "":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials for dev-bypass",
            )

    # Update last login timestamp
    user.last_login_at = datetime.now(UTC)
    db.commit()

    # Load user roles from database UserRole relations
    # If the user has no roles in the DB (like the default seeded user), fallback to default roles (admin, analyst)
    user_roles_str = [ur.role.name for ur in user.roles]
    if not user_roles_str:
        user_roles_str = [RoleName.admin.value, RoleName.analyst.value]

    roles_set = set()
    for role_name in user_roles_str:
        try:
            roles_set.add(RoleName(role_name))
        except ValueError:
            continue

    # Fallback to analyst role if empty
    if not roles_set:
        roles_set = {RoleName.analyst}

    token = create_access_token(
        subject=str(user.id),
        email=user.email,
        roles=roles_set,
        settings=settings,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        email=user.email,
        display_name=user.display_name or "User",
        roles=[role.value for role in roles_set],
    )
