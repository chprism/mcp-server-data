print("Testing imports...")
try:
    import stock_server
    print("Successfully imported stock_server")
except Exception as e:
    print(f"Error importing stock_server: {e}")

try:
    import analysis_system
    print("Successfully imported analysis_system")
except Exception as e:
    print(f"Error importing analysis_system: {e}")

print("Import test complete")
