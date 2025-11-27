"""Calculator tool for mathematical operations."""

from typing import Dict, Any
from .base import BaseTool


class CalculatorTool(BaseTool):
    """Tool for performing mathematical calculations."""
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "Perform mathematical calculations. Supports basic arithmetic operations (+, -, *, /), power (**), and parentheses."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate, e.g. '2 + 3 * 4', '(10 + 5) / 3', '2 ** 8'"
                }
            },
            "required": ["expression"]
        }
    
    async def execute(self, expression: str, **kwargs) -> str:
        """
        Evaluate a mathematical expression.
        
        Args:
            expression: Mathematical expression string
            **kwargs: Additional arguments (ignored)
            
        Returns:
            Calculation result as string
        """
        try:
            # 安全的数学表达式求值
            # 只允许数字、运算符和括号
            allowed_chars = set("0123456789+-*/().** ")
            if not all(c in allowed_chars for c in expression):
                return "错误：表达式包含不允许的字符。只支持数字和运算符 (+, -, *, /, **, ())"
            
            # 使用 eval 计算（在受控环境中）
            result = eval(expression, {"__builtins__": {}}, {})
            
            # 格式化结果
            if isinstance(result, float):
                # 如果是整数结果，不显示小数点
                if result.is_integer():
                    return f"{expression} = {int(result)}"
                else:
                    return f"{expression} = {result:.6f}".rstrip('0').rstrip('.')
            else:
                return f"{expression} = {result}"
                
        except ZeroDivisionError:
            return "错误：除数不能为零"
        except SyntaxError:
            return f"错误：无效的数学表达式 '{expression}'"
        except Exception as e:
            return f"错误：计算失败 - {str(e)}"
