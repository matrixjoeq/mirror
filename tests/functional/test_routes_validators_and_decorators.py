#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from app import create_app


class TestRoutesValidatorsAndDecorators(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.client = self.app.test_client()

    def test_trades_invalid_sort_and_dir_fallback(self):
        # 非法排序参数应回退到白名单默认列，不报错
        resp = self.client.get('/trades?sort=;DROP TABLE x;--&dir=weird')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'\xe4\xba\xa4\xe6\x98\x93\xe8\xae\xb0\xe5\xbd\x95', resp.data)  # 交易记录

    def test_trades_symbols_and_names_filters_parse(self):
        # 逗号与空白混合分隔的解析，不应500
        resp = self.client.get('/trades?symbols=aaa,%20bbb%20ccc&names=Alpha,%20Beta')
        self.assertEqual(resp.status_code, 200)

    def test_handle_errors_decorator_returns_json(self):
        # 触发一个已知错误路径（缺少确认码）验证装饰器 JSON 响应
        resp = self.client.post('/delete_trade/1', data={}, headers={'Content-Type': 'application/json'})
        self.assertEqual(resp.status_code, 400)
        # JSON 字符串包含“请提供确认码”（转义形式）
        self.assertIn(b'\\u8bf7\\u63d0\\u4f9b\\u786e\\u8ba4\\u7801', resp.data)


if __name__ == '__main__':
    unittest.main()


