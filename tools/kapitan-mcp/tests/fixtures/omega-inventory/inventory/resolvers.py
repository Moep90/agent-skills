def upper(value: str) -> str:
    """Custom resolver: uppercase its argument."""
    return str(value).upper()


def pass_resolvers() -> dict:
    """Return the custom resolvers this inventory registers.

    kapitan's omegaconf backend imports this module and calls this function,
    expecting a dict of {resolver_name: callable}.
    """
    return {"upper": upper}
