class ToolError(RuntimeError):
    exit_code = 1


class ConfigError(ToolError):
    exit_code = 2


class PrivilegeError(ToolError):
    exit_code = 3


class ProxyError(ToolError):
    exit_code = 4


class VerificationError(ToolError):
    exit_code = 5


class ShopifyError(ToolError):
    exit_code = 6


class PartialImportError(ToolError):
    exit_code = 7


class RestoreError(ToolError):
    exit_code = 8