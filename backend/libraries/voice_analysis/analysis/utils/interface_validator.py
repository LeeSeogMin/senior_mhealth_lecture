"""
API 인터페이스 호환성 검증 시스템
파라미터 불일치, 인터페이스 변경 감지 및 검증
"""

import inspect
import logging
from typing import Dict, Any, Callable, List, Optional
from functools import wraps
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class InterfaceSpec:
    """인터페이스 스펙 정의"""
    method_name: str
    required_params: List[str]
    optional_params: List[str]
    param_types: Dict[str, type]
    return_type: Optional[type] = None
    deprecated_params: List[str] = None

class InterfaceValidator:
    """인터페이스 검증기"""

    def __init__(self):
        self.registered_specs = {}
        self.validation_errors = []

    def register_interface(self, spec: InterfaceSpec):
        """인터페이스 스펙 등록"""
        self.registered_specs[spec.method_name] = spec

    def validate_call(self, method_name: str, args: tuple, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """함수 호출 검증"""
        if method_name not in self.registered_specs:
            logger.warning(f"Interface spec not found for {method_name}")
            return {'valid': True, 'warnings': [f'No spec registered for {method_name}']}

        spec = self.registered_specs[method_name]
        warnings = []
        errors = []

        # 필수 파라미터 검증
        provided_params = set(kwargs.keys())
        required_params = set(spec.required_params)

        missing_required = required_params - provided_params
        if missing_required:
            errors.append(f"Missing required parameters: {missing_required}")

        # Deprecated 파라미터 검증
        if spec.deprecated_params:
            deprecated_used = set(spec.deprecated_params) & provided_params
            if deprecated_used:
                warnings.append(f"Using deprecated parameters: {deprecated_used}")

        # 타입 검증
        for param_name, param_value in kwargs.items():
            if param_name in spec.param_types:
                expected_type = spec.param_types[param_name]
                if not isinstance(param_value, expected_type):
                    warnings.append(
                        f"Parameter {param_name} type mismatch: "
                        f"expected {expected_type.__name__}, got {type(param_value).__name__}"
                    )

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

def validate_interface(interface_name: str, validator: InterfaceValidator):
    """인터페이스 검증 데코레이터"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 검증 실행
            validation_result = validator.validate_call(interface_name, args, kwargs)

            # 에러가 있으면 예외 발생
            if not validation_result['valid']:
                raise ValueError(f"Interface validation failed: {validation_result['errors']}")

            # 경고 로깅
            for warning in validation_result['warnings']:
                logger.warning(f"Interface warning for {interface_name}: {warning}")

            return func(*args, **kwargs)

        return wrapper
    return decorator

class ParameterMigrator:
    """파라미터 마이그레이션 유틸리티"""

    def __init__(self):
        self.migration_rules = {}

    def add_migration_rule(self, old_param: str, new_param: str, converter: Callable = None):
        """마이그레이션 규칙 추가"""
        self.migration_rules[old_param] = {
            'new_param': new_param,
            'converter': converter or (lambda x: x)
        }

    def migrate_parameters(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """파라미터 마이그레이션 실행"""
        migrated = kwargs.copy()

        for old_param, rule in self.migration_rules.items():
            if old_param in migrated:
                old_value = migrated.pop(old_param)
                new_value = rule['converter'](old_value)
                migrated[rule['new_param']] = new_value

                logger.info(f"Migrated parameter: {old_param} -> {rule['new_param']}")

        return migrated

def with_parameter_migration(migrator: ParameterMigrator):
    """파라미터 마이그레이션 데코레이터"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            migrated_kwargs = migrator.migrate_parameters(kwargs)
            return func(*args, **migrated_kwargs)
        return wrapper
    return decorator

# 글로벌 인터페이스 검증기 인스턴스
global_validator = InterfaceValidator()
global_migrator = ParameterMigrator()

# MultiLLM 인터페이스 스펙 등록
global_validator.register_interface(InterfaceSpec(
    method_name='analyze_text',
    required_params=['text'],
    optional_params=['context', 'force_model'],
    param_types={
        'text': str,
        'context': dict,
        'force_model': str
    },
    deprecated_params=['force_openai']  # deprecated
))

# 파라미터 마이그레이션 규칙
global_migrator.add_migration_rule(
    'force_openai',
    'force_model',
    lambda x: 'openai' if x else None
)