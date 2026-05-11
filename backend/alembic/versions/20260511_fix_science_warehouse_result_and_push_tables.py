"""fix science warehouse result dimension and add push tables

Revision ID: 20260511_science_warehouse_push
Revises: None
Create Date: 2026-05-11 17:20:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260511_science_warehouse_push"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade():
    if _column_exists("calcu_science_warehouse_result", "product_model"):
        op.drop_column("calcu_science_warehouse_result", "product_model")
    if _column_exists("calcu_science_warehouse_result", "product_config_code"):
        op.drop_column("calcu_science_warehouse_result", "product_config_code")

    if not _table_exists("calcu_science_warehouse_push_result"):
        op.create_table(
            "calcu_science_warehouse_push_result",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键 ID"),
            sa.Column("calculation_id", sa.String(length=50), nullable=False, comment="计算批次ID"),
            sa.Column("warehouse_code", sa.String(length=255), nullable=False, comment="库房编码"),
            sa.Column("warehouse_name", sa.String(length=255), nullable=False, comment="库房名称"),
            sa.Column("spare_part_code", sa.String(length=255), nullable=False, comment="备品编码"),
            sa.Column("spare_part_name", sa.String(length=255), nullable=False, comment="备品名称"),
            sa.Column("max_failure_count", sa.Integer(), nullable=False, comment="最大滚动故障次数"),
            sa.Column("required_quantity", sa.Integer(), nullable=False, comment="需求数量"),
            sa.Column("calculation_method", sa.String(length=50), nullable=False, comment="计算方法"),
            sa.Column("time_interval_days", sa.Integer(), nullable=False, comment="时间间隔（天）"),
            sa.Column("input_date", sa.Date(), nullable=False, comment="计算截止日期"),
            sa.Column("created_time", sa.Date(), nullable=False, comment="原结果创建时间"),
            sa.Column("confidence", sa.Float(), nullable=False, comment="置信度"),
            sa.Column("imported_time", sa.DateTime(), nullable=False, comment="导入时间"),
            sa.Column("updated_time", sa.DateTime(timezone=True), nullable=True, comment="更新时间"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("id"),
            comment="科学库存待推送结果。",
        )

    if not _table_exists("calcu_science_warehouse_push_log"):
        op.create_table(
            "calcu_science_warehouse_push_log",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键 ID"),
            sa.Column("calculation_id", sa.String(length=50), nullable=False, comment="计算批次ID"),
            sa.Column("push_reason", sa.String(length=500), nullable=False, comment="推送原因"),
            sa.Column("push_status", sa.String(length=30), nullable=False, comment="推送状态"),
            sa.Column("chunk_no", sa.Integer(), nullable=False, comment="分包序号"),
            sa.Column("chunk_total", sa.Integer(), nullable=False, comment="分包总数"),
            sa.Column("total_records", sa.Integer(), nullable=False, comment="本次分包记录数"),
            sa.Column("request_id", sa.String(length=64), nullable=False, comment="ESB消息流水号"),
            sa.Column("track_id", sa.String(length=64), nullable=False, comment="ESB链路追踪号"),
            sa.Column("service_name", sa.String(length=128), nullable=False, comment="ESB服务名"),
            sa.Column("payload_size_bytes", sa.Integer(), nullable=False, comment="请求体字节数"),
            sa.Column("esb_status_flag", sa.String(length=10), nullable=True, comment="ESB状态标识"),
            sa.Column("esb_code", sa.String(length=50), nullable=True, comment="ESB响应码"),
            sa.Column("esb_desc", sa.String(length=500), nullable=True, comment="ESB响应描述"),
            sa.Column("response_body", sa.Text(), nullable=True, comment="响应体"),
            sa.Column("error_message", sa.Text(), nullable=True, comment="异常信息"),
            sa.Column("pushed_time", sa.DateTime(), nullable=True, comment="推送完成时间"),
            sa.Column("created_time", sa.DateTime(timezone=True), nullable=False, comment="创建时间"),
            sa.Column("updated_time", sa.DateTime(timezone=True), nullable=True, comment="更新时间"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("id"),
            comment="科学库存推送日志。",
        )

    indexes = [
        ("calcu_science_warehouse_push_result", "ix_calcu_science_warehouse_push_result_calculation_id", ["calculation_id"]),
        ("calcu_science_warehouse_push_result", "ix_calcu_science_warehouse_push_result_warehouse_code", ["warehouse_code"]),
        ("calcu_science_warehouse_push_result", "ix_calcu_science_warehouse_push_result_warehouse_name", ["warehouse_name"]),
        ("calcu_science_warehouse_push_result", "ix_calcu_science_warehouse_push_result_spare_part_code", ["spare_part_code"]),
        ("calcu_science_warehouse_push_result", "ix_calcu_science_warehouse_push_result_spare_part_name", ["spare_part_name"]),
        ("calcu_science_warehouse_push_log", "ix_calcu_science_warehouse_push_log_calculation_id", ["calculation_id"]),
        ("calcu_science_warehouse_push_log", "ix_calcu_science_warehouse_push_log_push_status", ["push_status"]),
        ("calcu_science_warehouse_push_log", "ix_calcu_science_warehouse_push_log_request_id", ["request_id"]),
        ("calcu_science_warehouse_push_log", "ix_calcu_science_warehouse_push_log_track_id", ["track_id"]),
    ]
    for table_name, index_name, columns in indexes:
        if _table_exists(table_name) and not _index_exists(table_name, index_name):
            op.create_index(index_name, table_name, columns, unique=False)


def downgrade():
    if _table_exists("calcu_science_warehouse_push_log"):
        op.drop_table("calcu_science_warehouse_push_log")
    if _table_exists("calcu_science_warehouse_push_result"):
        op.drop_table("calcu_science_warehouse_push_result")

    if _table_exists("calcu_science_warehouse_result"):
        if not _column_exists("calcu_science_warehouse_result", "product_model"):
            op.add_column(
                "calcu_science_warehouse_result",
                sa.Column("product_model", sa.String(length=128), nullable=True, comment="产品型号"),
            )
        if not _column_exists("calcu_science_warehouse_result", "product_config_code"):
            op.add_column(
                "calcu_science_warehouse_result",
                sa.Column("product_config_code", sa.String(length=128), nullable=True, comment="派生码"),
            )
