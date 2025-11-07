import os
import zipfile
import geopandas as gpd
from pathlib import Path

def convert_shapefiles_to_geojson():
    # Define paths
    base_dir = Path(__file__).parent.parent  # Get the project root directory
    shapefile_dir = base_dir / 'Shapefiles'
    output_dir = base_dir / 'data' / 'boundaries'
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each zip file in the Shapefiles directory
    for zip_path in shapefile_dir.glob('*.zip'):
        print(f"Processing {zip_path.name}...")
        
        # Create a temporary directory to extract the zip file
        temp_dir = shapefile_dir / 'temp'
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find all .shp files in the extracted contents
            shp_files = list(temp_dir.rglob('*.shp'))
            
            for shp_file in shp_files:
                # Read the shapefile
                gdf = gpd.read_file(shp_file)
                
                # Make sure geometries are valid
                gdf['geometry'] = gdf['geometry'].buffer(0)  # This fixes most common geometry issues
                
                # Create output filename (same as shapefile but with .geojson extension)
                output_filename = output_dir / f"{shp_file.stem}.geojson"
                
                # Convert to GeoJSON
                gdf.to_file(output_filename, driver='GeoJSON')
                print(f"Converted {shp_file.name} to {output_filename.name}")
                
        except Exception as e:
            print(f"Error processing {zip_path.name}: {str(e)}")
            
        finally:
            # Clean up: remove temporary extracted files
            if temp_dir.exists():
                for file in temp_dir.rglob('*'):
                    if file.is_file():
                        file.unlink()
                temp_dir.rmdir()

if __name__ == "__main__":
    convert_shapefiles_to_geojson()
    print("Conversion complete!")