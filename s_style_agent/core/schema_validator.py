"""
S式AST スキーマバリデータ

LLM出力のS式をJSON Schemaに基づいて検証し、
セキュリティとコンプライアンスをチェックする
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
import jsonschema
from jsonschema import validate, ValidationError
from langsmith import traceable

from ..config.settings import settings

SExpression = Union[str, int, float, bool, List[Any]]

class SecurityViolationError(Exception):
    """セキュリティ違反エラー"""
    pass

class SchemaValidationError(Exception):
    """スキーマ検証エラー"""
    pass

class SExpressionValidator:
    """S式AST バリデータ"""
    
    def __init__(self, schema_path: Optional[str] = None, validation_level: str = "strict"):
        """
        Args:
            schema_path: スキーマファイルのパス
            validation_level: 検証レベル ("strict", "permissive", "experimental")
        """
        self.validation_level = validation_level
        self.schema = self._load_schema(schema_path)
        self.security_rules = self._init_security_rules()
        
    def _load_schema(self, schema_path: Optional[str]) -> Dict[str, Any]:
        """JSON Schemaをロード"""
        if schema_path is None:
            # デフォルトスキーマパス
            schema_path = Path(__file__).parent.parent / "schema" / "s_expression_schema.json"
        
        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"スキーマファイルが見つかりません: {schema_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"スキーマファイルの解析エラー: {e}")
    
    def _init_security_rules(self) -> Dict[str, Any]:
        """セキュリティルールを初期化"""
        return {
            "forbidden_operations": [
                "__import__", "eval", "exec", "compile", "open", "file",
                "input", "raw_input", "reload", "vars", "globals", "locals",
                "delattr", "setattr", "getattr", "hasattr"
            ],
            "max_depth": 20,  # AST最大深度
            "max_nodes": 1000,  # AST最大ノード数
            "max_string_length": 10000,  # 文字列最大長
            "restricted_patterns": [
                r"__.*__",  # ダンダーメソッド
                r"import\s+",  # import文
                r"from\s+.*\s+import",  # from import文
                r"exec\s*\(",  # exec呼び出し
                r"eval\s*\(",  # eval呼び出し
            ]
        }
    
    @traceable(name="validate_s_expression")
    def validate(self, expr: SExpression, 
                 source: str = "unknown",
                 llm_model: str = "unknown") -> Tuple[bool, List[str]]:
        """
        S式を検証
        
        Args:
            expr: 検証するS式
            source: 生成元（"llm", "user", "system"等）
            llm_model: 使用したLLMモデル名
            
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        try:
            # 1. セキュリティチェック
            security_errors = self._check_security(expr)
            errors.extend(security_errors)
            
            # 2. 構造チェック
            structure_errors = self._check_structure(expr)
            errors.extend(structure_errors)
            
            # 3. JSON Schema バリデーション
            schema_errors = self._validate_schema(expr)
            errors.extend(schema_errors)
            
            # 4. 検証レベル別チェック
            level_errors = self._validate_by_level(expr)
            errors.extend(level_errors)
            
            is_valid = len(errors) == 0
            
            # 検証結果をログ
            self._log_validation_result(expr, is_valid, errors, source, llm_model)
            
            return is_valid, errors
            
        except Exception as e:
            error_msg = f"検証中にエラーが発生: {str(e)}"
            return False, [error_msg]
    
    def _check_security(self, expr: SExpression) -> List[str]:
        """セキュリティチェック"""
        errors = []
        
        def check_node(node: Any, depth: int = 0) -> None:
            if depth > self.security_rules["max_depth"]:
                errors.append(f"AST深度が制限を超えています: {depth} > {self.security_rules['max_depth']}")
                return
            
            if isinstance(node, str):
                # 文字列長チェック
                if len(node) > self.security_rules["max_string_length"]:
                    errors.append(f"文字列が長すぎます: {len(node)} > {self.security_rules['max_string_length']}")
                
                # 禁止操作チェック
                if node in self.security_rules["forbidden_operations"]:
                    errors.append(f"禁止された操作: {node}")
                
                # パターンマッチング
                import re
                for pattern in self.security_rules["restricted_patterns"]:
                    if re.search(pattern, node, re.IGNORECASE):
                        errors.append(f"禁止されたパターン: '{pattern}' in '{node}'")
            
            elif isinstance(node, list):
                for item in node:
                    check_node(item, depth + 1)
        
        # ノード数カウント
        node_count = self._count_nodes(expr)
        if node_count > self.security_rules["max_nodes"]:
            errors.append(f"ASTノード数が制限を超えています: {node_count} > {self.security_rules['max_nodes']}")
        
        check_node(expr)
        return errors
    
    def _check_structure(self, expr: SExpression) -> List[str]:
        """構造チェック"""
        errors = []
        
        def validate_structure(node: Any, path: str = "root") -> None:
            if isinstance(node, list):
                if len(node) == 0:
                    errors.append(f"空のリストは無効です: {path}")
                    return
                
                # 演算子チェック
                op = node[0]
                if not isinstance(op, str):
                    errors.append(f"演算子は文字列である必要があります: {path}[0] = {type(op)}")
                    return
                
                # 各演算子の引数数チェック
                arg_count = len(node) - 1
                op_requirements = {
                    "seq": {"min": 1, "max": None},
                    "par": {"min": 1, "max": None},
                    "if": {"min": 2, "max": 3},
                    "handle": {"min": 3, "max": 3},
                    "while": {"min": 2, "max": 3},
                    "let": {"min": 2, "max": 2},
                    "set": {"min": 2, "max": 2},
                    "+": {"min": 2, "max": None},
                    "<": {"min": 2, "max": 2},
                    "notify": {"min": 1, "max": 1},
                    "calc": {"min": 1, "max": 1},
                    "ask_user": {"min": 1, "max": 3}
                }
                
                if op in op_requirements:
                    req = op_requirements[op]
                    if arg_count < req["min"]:
                        errors.append(f"'{op}'の引数が不足: {path} (必要: {req['min']}個以上, 実際: {arg_count}個)")
                    if req["max"] is not None and arg_count > req["max"]:
                        errors.append(f"'{op}'の引数が過多: {path} (最大: {req['max']}個, 実際: {arg_count}個)")
                
                # 再帰的チェック
                for i, child in enumerate(node[1:], 1):
                    validate_structure(child, f"{path}[{i}]")
        
        validate_structure(expr)
        return errors
    
    def _validate_schema(self, expr: SExpression) -> List[str]:
        """JSON Schema バリデーション"""
        errors = []
        
        try:
            # ASTを検証用フォーマットに変換
            validation_obj = {
                "ast": expr,
                "metadata": {"version": "1.0.0"}
            }
            
            # Schema検証実行
            validate(instance=validation_obj, schema=self.schema)
            
        except ValidationError as e:
            errors.append(f"スキーマ検証エラー: {e.message} (パス: {' -> '.join(str(p) for p in e.absolute_path)})")
        except Exception as e:
            errors.append(f"スキーマ検証中にエラー: {str(e)}")
        
        return errors
    
    def _validate_by_level(self, expr: SExpression) -> List[str]:
        """検証レベル別チェック"""
        errors = []
        
        if self.validation_level == "strict":
            # 厳格モード: 実験的機能禁止
            experimental_ops = ["db-query"]  # 実験的操作
            if isinstance(expr, list) and len(expr) > 0 and expr[0] in experimental_ops:
                errors.append(f"厳格モードでは実験的操作は禁止: {expr[0]}")
        
        elif self.validation_level == "experimental":
            # 実験的モード: 警告のみ
            if isinstance(expr, list) and len(expr) > 0:
                op = expr[0]
                if op not in ["seq", "par", "if", "let", "notify", "calc", "+", "<"]:
                    # 警告として記録（エラーにしない）
                    print(f"[警告] 実験的操作を使用: {op}")
        
        return errors
    
    def _count_nodes(self, expr: SExpression) -> int:
        """ASTのノード数をカウント"""
        if isinstance(expr, list):
            return 1 + sum(self._count_nodes(item) for item in expr)
        else:
            return 1
    
    def _log_validation_result(self, expr: SExpression, is_valid: bool, 
                              errors: List[str], source: str, llm_model: str) -> None:
        """検証結果をログ"""
        if settings.system.debug:
            result_str = "成功" if is_valid else "失敗"
            print(f"[スキーマ検証] {result_str} - ソース: {source}, モデル: {llm_model}")
            if errors:
                for error in errors:
                    print(f"  エラー: {error}")

class LLMOutputGate:
    """LLM出力ゲート検証器"""
    
    def __init__(self, validation_level: str = "strict"):
        self.validator = SExpressionValidator(validation_level=validation_level)
        self.blocked_count = 0
        self.allowed_count = 0
    
    @traceable(name="llm_output_gate")
    def validate_llm_output(self, raw_output: str, llm_model: str = "unknown") -> Tuple[bool, SExpression, List[str]]:
        """
        LLM出力を検証してS式として承認/拒否
        
        Args:
            raw_output: LLMの生成テキスト
            llm_model: 使用したLLMモデル名
            
        Returns:
            (is_approved, parsed_expr, error_messages)
        """
        errors = []
        
        try:
            # 1. S式パース
            from .parser import parse_s_expression
            parsed_expr = parse_s_expression(raw_output)
            
            # 2. スキーマ検証
            is_valid, validation_errors = self.validator.validate(
                parsed_expr, source="llm", llm_model=llm_model
            )
            
            if is_valid:
                self.allowed_count += 1
                return True, parsed_expr, []
            else:
                self.blocked_count += 1
                return False, None, validation_errors
                
        except Exception as e:
            self.blocked_count += 1
            error_msg = f"LLM出力の解析/検証エラー: {str(e)}"
            return False, None, [error_msg]
    
    def get_stats(self) -> Dict[str, int]:
        """統計情報を取得"""
        total = self.allowed_count + self.blocked_count
        return {
            "allowed": self.allowed_count,
            "blocked": self.blocked_count,
            "total": total,
            "block_rate": self.blocked_count / total if total > 0 else 0.0
        }