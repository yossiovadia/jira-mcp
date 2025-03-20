try:
  import pypdf
  print(f"pypdf imported successfully: {pypdf.__version__}")
except ImportError as e:
  print(f"Error importing pypdf: {e}")
