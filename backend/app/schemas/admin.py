from pydantic import BaseModel


class VerificationLogResponse(BaseModel):
    id: int
    user_id: int
    username: str
    timestamp: str
    success: bool
    detection: bool
    image_width: int
    image_height: int
    file_size_bytes: float
    input_age: int
    back_color: str | None
    error_message: str | None = None
    image_path: str | None = None


class PaginatedLogs(BaseModel):
    items: list[VerificationLogResponse]
    total: int
    page: int
    per_page: int
    pages: int


class DailyChartItem(BaseModel):
    date: str
    count: int


class DashboardStats(BaseModel):
    total_verifications: int
    today_verifications: int
    week_verifications: int
    success_rate: float
    unique_users: int
    daily_chart: list[DailyChartItem]
