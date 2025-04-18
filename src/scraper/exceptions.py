class AccessRestrictedError(Exception):
    """Exception raised when access to a resource is restricted."""
    def __init__(self, message="Access to the requested resource is restricted"):
        self.message = message
        super().__init__(self.message)