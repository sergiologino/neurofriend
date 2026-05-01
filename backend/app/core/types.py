from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB


jsonb_type = JSONB().with_variant(JSON(), "sqlite")
