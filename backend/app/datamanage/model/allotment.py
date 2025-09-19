from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, DataClassBase, id_key


class Allotment(DataClassBase):
    __tablename__ = 'dm_allotment'
    
    id: Mapped[id_key] = mapped_column(init=False)
    vehicle_type: Mapped[str] = mapped_column(String(255), nullable=False, comment='车型')
    vehicle_number: Mapped[str] = mapped_column(String(255), nullable=False, comment='车号')
    product_model: Mapped[str] = mapped_column(String(255), nullable=False, comment='产品型号')
    ps_code: Mapped[str] = mapped_column(String(255), nullable=True, comment='派生码')
    product_number: Mapped[str] = mapped_column(String(255), nullable=False, comment='产品编号')
    allotment_one: Mapped[str] = mapped_column(String(255), nullable=True, comment='一级配属')
    allotment_two: Mapped[str] = mapped_column(String(255), nullable=True, comment='二级配属')
    allotment_date: Mapped[date] = mapped_column(Date, nullable=True, comment='配属日期')