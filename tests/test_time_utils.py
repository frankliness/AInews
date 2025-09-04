"""
Phoenix time_utils 模块的单元测试

测试北京时间6AM日界逻辑的正确性，包括边界条件和各种时间转换场景。
"""

import unittest
import os
from datetime import datetime, date
from zoneinfo import ZoneInfo
import sys

# 添加项目根目录到Python路径，以便导入dags模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dags.phoenix.time_utils import (
    get_cutoff_hour, utc_to_bj, logical_date_bj, 
    prev_logical_date_str, now_prev_logical_date_str
)


class TestTimeUtils(unittest.TestCase):
    """测试time_utils模块的核心功能"""
    
    def setUp(self):
        """测试前的设置"""
        # 清理可能存在的环境变量
        if 'BJ_CUTOFF_HOUR' in os.environ:
            del os.environ['BJ_CUTOFF_HOUR']
    
    def test_get_cutoff_hour_default(self):
        """测试默认cutoff值"""
        self.assertEqual(get_cutoff_hour(), 6)
    
    def test_get_cutoff_hour_from_env(self):
        """测试从环境变量获取cutoff值"""
        os.environ['BJ_CUTOFF_HOUR'] = '8'
        self.assertEqual(get_cutoff_hour(), 8)
        
        os.environ['BJ_CUTOFF_HOUR'] = '0'
        self.assertEqual(get_cutoff_hour(), 0)
        
        os.environ['BJ_CUTOFF_HOUR'] = '23'
        self.assertEqual(get_cutoff_hour(), 23)
    
    def test_get_cutoff_hour_invalid_env(self):
        """测试无效的环境变量值"""
        os.environ['BJ_CUTOFF_HOUR'] = 'invalid'
        self.assertEqual(get_cutoff_hour(), 6)
        
        os.environ['BJ_CUTOFF_HOUR'] = '25'
        self.assertEqual(get_cutoff_hour(), 6)
        
        os.environ['BJ_CUTOFF_HOUR'] = '-1'
        self.assertEqual(get_cutoff_hour(), 6)
    
    def test_get_cutoff_hour_from_var_fn(self):
        """测试从Airflow Variable函数获取cutoff值"""
        def mock_var_fn(key):
            if key == 'bj_cutoff_hour':
                return '10'
            return None
        
        self.assertEqual(get_cutoff_hour(mock_var_fn), 10)
    
    def test_get_cutoff_hour_var_fn_exception(self):
        """测试Airflow Variable函数异常时的回退"""
        def mock_var_fn(key):
            raise Exception("Variable not found")
        
        self.assertEqual(get_cutoff_hour(mock_var_fn), 6)
    
    def test_utc_to_bj_aware(self):
        """测试aware UTC时间转换为北京时间"""
        utc_dt = datetime(2025, 9, 1, 16, 5, tzinfo=ZoneInfo("UTC"))
        bj_dt = utc_to_bj(utc_dt)
        
        self.assertEqual(bj_dt.year, 2025)
        self.assertEqual(bj_dt.month, 9)
        self.assertEqual(bj_dt.day, 2)
        self.assertEqual(bj_dt.hour, 0)
        self.assertEqual(bj_dt.minute, 5)
        self.assertEqual(bj_dt.tzinfo, ZoneInfo("Asia/Shanghai"))
    
    def test_utc_to_bj_naive(self):
        """测试naive UTC时间转换为北京时间"""
        utc_dt = datetime(2025, 9, 1, 16, 5)  # naive
        bj_dt = utc_to_bj(utc_dt)
        
        self.assertEqual(bj_dt.year, 2025)
        self.assertEqual(bj_dt.month, 9)
        self.assertEqual(bj_dt.day, 2)
        self.assertEqual(bj_dt.hour, 0)
        self.assertEqual(bj_dt.minute, 5)
        self.assertEqual(bj_dt.tzinfo, ZoneInfo("Asia/Shanghai"))
    
    def test_logical_date_bj_basic_cases(self):
        """测试logical_date_bj的基本用例"""
        # 测试用例1: UTC 2025-09-01 16:05:00 -> BJ 2025-09-02 00:05 -> 返回 2025-09-01
        dt1 = datetime(2025, 9, 1, 16, 5, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(logical_date_bj(dt1, 6), date(2025, 9, 1))
        
        # 测试用例2: UTC 2025-09-01 21:59:00 -> BJ 2025-09-02 05:59 -> 返回 2025-09-01
        dt2 = datetime(2025, 9, 1, 21, 59, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(logical_date_bj(dt2, 6), date(2025, 9, 1))
        
        # 测试用例3: UTC 2025-09-01 22:00:00 -> BJ 2025-09-02 06:00 -> 返回 2025-09-02
        dt3 = datetime(2025, 9, 1, 22, 0, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(logical_date_bj(dt3, 6), date(2025, 9, 2))
    
    def test_logical_date_bj_edge_cases(self):
        """测试logical_date_bj的边界情况"""
        # 测试用例4: UTC 2025-02-28 21:00:00 -> BJ 2025-03-01 05:00 -> 返回 2025-02-28
        dt4 = datetime(2025, 2, 28, 21, 0, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(logical_date_bj(dt4, 6), date(2025, 2, 28))
        
        # 测试用例5: UTC 2025-03-31 22:30:00 -> BJ 2025-04-01 06:30 -> 返回 2025-04-01
        dt5 = datetime(2025, 3, 31, 22, 30, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(logical_date_bj(dt5, 6), date(2025, 4, 1))
    
    def test_logical_date_bj_different_cutoff(self):
        """测试不同cutoff值的logical_date_bj"""
        # cutoff=8的情况
        dt = datetime(2025, 9, 1, 20, 0, tzinfo=ZoneInfo("UTC"))  # BJ 2025-09-02 04:00
        self.assertEqual(logical_date_bj(dt, 8), date(2025, 9, 1))  # 4:00 < 8:00，计入前日
        
        dt = datetime(2025, 9, 1, 22, 0, tzinfo=ZoneInfo("UTC"))  # BJ 2025-09-02 06:00
        self.assertEqual(logical_date_bj(dt, 8), date(2025, 9, 1))  # 6:00 < 8:00，计入前日
        
        dt = datetime(2025, 9, 1, 23, 0, tzinfo=ZoneInfo("UTC"))  # BJ 2025-09-02 07:00
        self.assertEqual(logical_date_bj(dt, 8), date(2025, 9, 1))  # 7:00 < 8:00，计入前日
        
        dt = datetime(2025, 9, 2, 0, 0, tzinfo=ZoneInfo("UTC"))  # BJ 2025-09-02 08:00
        self.assertEqual(logical_date_bj(dt, 8), date(2025, 9, 2))  # 8:00 >= 8:00，计入当日
    
    def test_prev_logical_date_str(self):
        """测试prev_logical_date_str函数"""
        # 运行时间：UTC 2025-09-02 00:30 -> BJ 2025-09-02 08:30 -> 前一日为 2025-09-01
        run_dt = datetime(2025, 9, 2, 0, 30, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(prev_logical_date_str(run_dt, 6), "2025-09-01")
        
        # 运行时间：UTC 2025-09-02 22:00 -> BJ 2025-09-03 06:00 -> 前一日为 2025-09-02
        run_dt2 = datetime(2025, 9, 2, 22, 0, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(prev_logical_date_str(run_dt2, 6), "2025-09-02")
    
    def test_prev_logical_date_str_different_cutoff(self):
        """测试不同cutoff值的prev_logical_date_str"""
        # cutoff=8的情况
        run_dt = datetime(2025, 9, 2, 0, 0, tzinfo=ZoneInfo("UTC"))  # BJ 2025-09-02 08:00
        self.assertEqual(prev_logical_date_str(run_dt, 8), "2025-09-01")
        
        run_dt2 = datetime(2025, 9, 2, 1, 0, tzinfo=ZoneInfo("UTC"))  # BJ 2025-09-02 09:00
        self.assertEqual(prev_logical_date_str(run_dt2, 8), "2025-09-01")
    
    def test_now_prev_logical_date_str(self):
        """测试now_prev_logical_date_str函数"""
        # 这个测试比较难精确验证，因为依赖于当前时间
        # 我们主要验证函数能正常执行并返回正确格式的字符串
        result = now_prev_logical_date_str(6)
        self.assertIsInstance(result, str)
        self.assertRegex(result, r'^\d{4}-\d{2}-\d{2}$')  # 验证格式为YYYY-MM-DD
        
        # 验证不同cutoff值
        result2 = now_prev_logical_date_str(8)
        self.assertIsInstance(result2, str)
        self.assertRegex(result2, r'^\d{4}-\d{2}-\d{2}$')


class TestTimeUtilsIntegration(unittest.TestCase):
    """集成测试，验证多个函数的组合使用"""
    
    def test_consistent_behavior(self):
        """测试函数间的一致性行为"""
        # 验证logical_date_bj和prev_logical_date_str的一致性
        test_dt = datetime(2025, 9, 1, 21, 59, tzinfo=ZoneInfo("UTC"))
        
        # 这个时间应该属于2025-09-01的逻辑日期
        logical_date = logical_date_bj(test_dt, 6)
        self.assertEqual(logical_date, date(2025, 9, 1))
        
        # 如果我们在2025-09-02运行，前一日应该是2025-09-01
        run_dt = datetime(2025, 9, 2, 0, 30, tzinfo=ZoneInfo("UTC"))
        prev_date_str = prev_logical_date_str(run_dt, 6)
        self.assertEqual(prev_date_str, "2025-09-01")
    
    def test_cutoff_consistency(self):
        """测试cutoff参数在不同函数间的一致性"""
        cutoff = 8
        
        # 使用相同的cutoff值测试多个函数
        test_dt = datetime(2025, 9, 1, 20, 0, tzinfo=ZoneInfo("UTC"))
        logical_date = logical_date_bj(test_dt, cutoff)
        
        run_dt = datetime(2025, 9, 2, 0, 0, tzinfo=ZoneInfo("UTC"))
        prev_date_str = prev_logical_date_str(run_dt, cutoff)
        
        # 验证结果的一致性
        self.assertIsInstance(logical_date, date)
        self.assertIsInstance(prev_date_str, str)
        self.assertRegex(prev_date_str, r'^\d{4}-\d{2}-\d{2}$')


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
