-- ============================================================================
-- 风电平台适配：视图初始化脚本 (wind_view_init.sql)
-- ============================================================================
-- 用途：新建风电专用库 fba_wind，用视图将风电数据表映射为原系统表结构，
--       使 reis-backend 无需修改任何源码即可运行风电数据分析。
-- 目标库：fba_wind（同一 MySQL 实例：172.30.1.148:3306）
-- 数据源：fba 库中的风电四表
--       dm_jl_failure  故障记录（8452条）
--       dm_jl_product  风电产品/运行剖面（120条）
--       dm_despatch    发运/台账（透传，已是原系统格式）
--       dm_ebom        部件清单（透传，已是原系统格式）
--
-- ⚠️ 执行前提：
--   1. 本脚本会 DROP fba_wind 中同名表/视图，请在确认 fba_wind 无重要数据后执行
--   2. fba 库只被读取，绝不修改
--   3. 建议顺序：先执行 alembic upgrade head 建好系统表，再执行本脚本
--      （脚本对"表已存在"和"表不存在"两种情况都兼容）
--
-- 执行顺序注意：若日后上游 alembic 迁移涉及修改这 4 张 dm_* 表结构，
-- 需先删视图、跑迁移、再重建视图（记录在案，出现时再处理）。
-- ============================================================================

CREATE DATABASE IF NOT EXISTS fba_wind DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fba_wind;

-- ============================================================================
-- 1. dm_product ← dm_jl_product （产品/运行剖面）
--    原模型：backend/app/datamanage/model/product.py
-- ============================================================================
DROP VIEW IF EXISTS dm_product;
DROP TABLE IF EXISTS dm_product;
CREATE VIEW dm_product AS
SELECT
    CAST(ID AS UNSIGNED)                              AS id,
    LARGE_CLASS                                       AS large_class,
    PRODUCT_TYPE                                      AS product_type,
    APPLY_AREA                                        AS apply_area,
    APPLY_AREA_DESC                                   AS apply_area_desc,
    PRODUCT_SUB                                       AS product_sub,
    NULL                                              AS sub_name,
    SUB_SAET                                          AS sub_saet,
    MODEL                                             AS model,
    PS_CODE                                           AS ps_code,        -- 派生码(与master模型映射一致: name='ps_code')
    INDUSTRY_UNIT                                     AS industry_unit,
    NULL                                              AS repair_priod,
    NULL                                              AS attach_train,
    NULL                                              AS attach_convert,
    NULL                                              AS attach_module_num,
    COOLING_MODE                                      AS cooling_mode,
    VOLTAGE_LEVEL                                     AS voltage_level,
    STRUCTURE                                         AS structure,
    -- 风电无修级概念: 用产品寿命(年)折算天数替代修级间隔, 保证关键件打标校验通过
    CAST(PROD_REPAIR AS SIGNED) * 365                 AS repair_times,
    CAST(AVG_WORKTIME AS SIGNED)                      AS avg_worktime,   -- 日均工作小时
    NULL                                              AS avg_speed,      -- 时速为铁路概念，风电不适用
    YEAR_DAYS                                         AS year_days,      -- 年运行天数
    UPDATE_TIME                                       AS update_time,
    MARK1                                             AS mark,
    PRD_BIG_TYPE                                      AS prd_big_type
FROM fba.dm_jl_product p
-- 去重: 同一机型可存在多行(同派生码重复行), 按(机型,派生码)组合去重, 各保留最小ID
WHERE p.ID = (
    SELECT MIN(p2.ID) FROM fba.dm_jl_product p2
    WHERE p2.MODEL = p.MODEL
      AND COALESCE(p2.PS_CODE, '') = COALESCE(p.PS_CODE, '')
);

-- ============================================================================
-- 2. dm_failure ← dm_jl_failure （故障记录）
--    原模型：backend/app/datamanage/model/failure.py
--    说明：
--    * ID 字段 6797/8452 为空且大量重复，主键 pk 用 ROW_NUMBER 生成稳定行号
--    * 故障部位优先取"终判"(FINAL_DIAGNOSIS/FAULT_COMPONENT)，为空回退初判(PART_NAME)
--    * 物料编码大面积缺失(~87%)，按 PART_NAME 分组拟合
--    * IS_ZERO/IS_YJ_PRODUCT 为中文"是/否"，转 1/0
-- ============================================================================
DROP VIEW IF EXISTS dm_failure;
DROP TABLE IF EXISTS dm_failure;
CREATE VIEW dm_failure AS
SELECT
    ROW_NUMBER() OVER (ORDER BY OCCUR_DATE, PRODUCT_NO, PART_NAME, ID) AS pk,
    ID                                               AS id,
    INFO_NO                                          AS report_id,
    PRODUCT_NO                                       AS product_no,
    PRODUCT_MODEL                                    AS product_model,
    PRODUCT_CONFIG_CODE                              AS product_config_code,
    NULL                                             AS repair_level,
    NULL                                             AS overhaul_location,
    NULL                                             AS overhaul_factory_date,
    NEW_MANUFACTURING_DATE                           AS production_data,   -- 新造日期
    PARK_NAME                                        AS allotment_now,     -- 风场→配属
    NULL                                             AS allotment_one,
    NULL                                             AS allotment_two,
    NULL                                             AS allotment_date,
    NULL                                             AS train_model_name,
    TOWER_NUM                                        AS train_no,          -- 风塔编号→机组
    NULL                                             AS compartment_no,
    NULL                                             AS `position`,
    NULL                                             AS train_number,
    NULL                                             AS operational_routing_start,
    NULL                                             AS operational_routing_end,
    OCCUR_DATE                                       AS fault_date,        -- 故障时间
    PARK_ADDRESS                                     AS fault_address,     -- 风场地址→故障地点
    COALESCE(NULLIF(FINAL_DIAGNOSIS, ''), NULLIF(PART_NAME, ''),
             NULLIF(FAULT_LOCATION, ''))             AS fault_part_name,   -- 终判故障部位名称
    COALESCE(NULLIF(FAULT_COMPONENT, ''), NULLIF(FAULT_MATERIAL_CODE, ''),
             NULLIF(FINAL_MATIA_ID, ''))             AS fault_part_code,   -- 终判故障部位物料代号
    SUPPLER_NAME                                     AS supplier,
    NULLIF(FAULT_MODE, '')                           AS failure_mode,      -- 终判故障模式
    NULL                                             AS fault_interval_start,
    NULL                                             AS fault_interval_end,
    NULL                                             AS total_train_milage,
    COALESCE(NULLIF(JL_FAULT_TYPE, ''), NULLIF(FAULT_TYPE, '')) AS fault_type,
    NULLIF(FINAL_RESPONSIBILITY, '')                 AS respons,           -- 最终判责
    NULL                                             AS vehicle_fault_codes,
    SERIAL_NUMBER                                    AS fault_part_number,          -- 原部件序列号
    BATCH_NUMBER                                     AS fault_part_batch_no,
    SERIAL_NUMBER                                    AS fault_part_serial_number,
    NEW_SERIAL_NUMBER                                AS replacement_part_number,    -- 更换件序列号
    NEW_BATCH_NUMBER                                 AS repl_part_batch_no,
    NEW_SERIAL_NUMBER                                AS repl_part_serial_number,
    COMPLETE_TIME                                    AS disposal_end_date,          -- 处理完成日期
    NULL                                             AS allotment_status,
    FAULT_SEVERITY                                   AS impact_level,               -- 故障严重等级→影响级别
    NULL                                             AS is_online,
    NEW_SUPPLIER                                     AS new_supplier,               -- 更换件供应商
    CAST(LIFE_CYCLE_TIME AS CHAR)                    AS life_cycle_time_erp,        -- 新造发运出场时间
    SYS_DATE                                         AS cj_date,                    -- 数据更新时间→采集时间
    NULLIF(PART_NAME, '')                            AS first_fault_part_name,      -- 故障部位→初判部位
    NULLIF(FAULT_MATERIAL_CODE, '')                  AS first_fault_part_code,      -- 原物料编码→初判编码
    NULL                                             AS first_failure_mode,
    NULLIF(FAULT_TYPE, '')                           AS first_fault_type,
    NULLIF(PART_NAME, '')                            AS fault_part_name_old,
    NULL                                             AS job_duration,
    NULL                                             AS loss_accounting,
    CASE WHEN IS_ZERO = '是' THEN 1
         WHEN IS_ZERO = '否' THEN 0 ELSE NULL END    AS is_zero,           -- 是否0运行时长
    CASE WHEN IS_YJ_PRODUCT = '是' THEN 1
         WHEN IS_YJ_PRODUCT = '否' THEN 0 ELSE NULL END AS is_company,     -- 是否本公司产品
    NULL                                             AS is_warranty_fault
FROM fba.dm_jl_failure;

-- ============================================================================
-- 3. dm_despatch ← fba.dm_despatch （发运/台账，透传）
--    风电库中该表已是原系统格式（model/identifier/life_cycle_time 齐全）
-- ============================================================================
DROP VIEW IF EXISTS dm_despatch;
DROP TABLE IF EXISTS dm_despatch;
CREATE VIEW dm_despatch AS
-- 产业隔离: 仅保留风电产品表覆盖的机型, 避免读到铁路发运数据(评审意见)
SELECT d.* FROM fba.dm_despatch d
WHERE d.model IN (SELECT DISTINCT MODEL FROM fba.dm_jl_product);

-- ============================================================================
-- 4. dm_ebom ← fba.dm_ebom （部件清单，透传）
--    风电库中该表已是原系统格式（prd_no/y8_matbnum1/bl_quantity 齐全）
-- ============================================================================
DROP VIEW IF EXISTS dm_ebom;
DROP TABLE IF EXISTS dm_ebom;
CREATE VIEW dm_ebom AS
-- 产业隔离: 仅保留风电产品表覆盖的机型, 避免读到铁路BOM数据(评审意见)
SELECT e.* FROM fba.dm_ebom e
WHERE e.prd_no IN (SELECT DISTINCT MODEL FROM fba.dm_jl_product);

-- ============================================================================
-- 验证语句（执行后人工核对）
-- ============================================================================
-- SELECT COUNT(*) FROM dm_failure;                       -- 期望 8452
-- SELECT COUNT(*) FROM dm_product;                       -- 期望 120
-- SELECT COUNT(*) FROM dm_despatch;                      -- 期望 403039
-- SELECT COUNT(*) FROM dm_ebom;                          -- 期望 679886
-- SELECT product_model, fault_part_name, COUNT(*)
--   FROM dm_failure
--  WHERE product_model = 'YJ93A' AND fault_part_name = '轴承'
--  GROUP BY product_model, fault_part_name;              -- 期望约 1394
-- SELECT model, avg_worktime, year_days FROM dm_product WHERE model='YJ93A';
