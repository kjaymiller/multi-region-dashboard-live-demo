"""Script to populate locations table with region data from region_mapping.py"""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent))

from app.database import get_connection
from app.config import get_dsn
from app.region_mapping import REGION_COORDINATES

# Enhanced region data with additional information
LOCATION_DATA = [
    # AWS Regions
    {"region_code": "us-east-1", "region_name": "US East (N. Virginia)", "cloud_provider": "AWS", "country": "United States", "city": "Northern Virginia", "description": "AWS US East - Northern Virginia"},
    {"region_code": "us-east-2", "region_name": "US East (Ohio)", "cloud_provider": "AWS", "country": "United States", "city": "Ohio", "description": "AWS US East - Ohio"},
    {"region_code": "us-west-1", "region_name": "US West (N. California)", "cloud_provider": "AWS", "country": "United States", "city": "Northern California", "description": "AWS US West - Northern California"},
    {"region_code": "us-west-2", "region_name": "US West (Oregon)", "cloud_provider": "AWS", "country": "United States", "city": "Oregon", "description": "AWS US West - Oregon"},
    {"region_code": "us-central-1", "region_name": "US Central (Illinois)", "cloud_provider": "AWS", "country": "United States", "city": "Illinois", "description": "AWS US Central - Illinois"},
    {"region_code": "ca-central-1", "region_name": "Canada (Central)", "cloud_provider": "AWS", "country": "Canada", "city": "Central", "description": "AWS Canada Central"},
    {"region_code": "eu-west-1", "region_name": "EU West (Ireland)", "cloud_provider": "AWS", "country": "Ireland", "city": "Dublin", "description": "AWS EU West - Ireland"},
    {"region_code": "eu-west-2", "region_name": "EU West (London)", "cloud_provider": "AWS", "country": "United Kingdom", "city": "London", "description": "AWS EU West - London"},
    {"region_code": "eu-central-1", "region_name": "EU Central (Frankfurt)", "cloud_provider": "AWS", "country": "Germany", "city": "Frankfurt", "description": "AWS EU Central - Frankfurt"},
    {"region_code": "eu-north-1", "region_name": "EU North (Stockholm)", "cloud_provider": "AWS", "country": "Sweden", "city": "Stockholm", "description": "AWS EU North - Stockholm"},
    {"region_code": "eu-south-1", "region_name": "EU South (Italy)", "cloud_provider": "AWS", "country": "Italy", "city": "Milan", "description": "AWS EU South - Italy"},
    {"region_code": "ap-southeast-1", "region_name": "AP Southeast (Singapore)", "cloud_provider": "AWS", "country": "Singapore", "city": "Singapore", "description": "AWS AP Southeast - Singapore"},
    {"region_code": "ap-southeast-2", "region_name": "AP Southeast (Sydney)", "cloud_provider": "AWS", "country": "Australia", "city": "Sydney", "description": "AWS AP Southeast - Sydney"},
    {"region_code": "ap-northeast-1", "region_name": "AP Northeast (Tokyo)", "cloud_provider": "AWS", "country": "Japan", "city": "Tokyo", "description": "AWS AP Northeast - Tokyo"},
    {"region_code": "ap-northeast-2", "region_name": "AP Northeast (Seoul)", "cloud_provider": "AWS", "country": "South Korea", "city": "Seoul", "description": "AWS AP Northeast - Seoul"},
    {"region_code": "ap-south-1", "region_name": "AP South (Mumbai)", "cloud_provider": "AWS", "country": "India", "city": "Mumbai", "description": "AWS AP South - Mumbai"},
    {"region_code": "me-south-1", "region_name": "ME South (Bahrain)", "cloud_provider": "AWS", "country": "Bahrain", "city": "Manama", "description": "AWS ME South - Bahrain"},
    {"region_code": "af-south-1", "region_name": "AF South (Cape Town)", "cloud_provider": "AWS", "country": "South Africa", "city": "Cape Town", "description": "AWS AF South - Cape Town"},
    {"region_code": "sa-east-1", "region_name": "SA East (São Paulo)", "cloud_provider": "AWS", "country": "Brazil", "city": "São Paulo", "description": "AWS SA East - São Paulo"},

    # GCP Regions
    {"region_code": "us-central1", "region_name": "US Central (Iowa)", "cloud_provider": "GCP", "country": "United States", "city": "Iowa", "description": "GCP US Central - Iowa"},
    {"region_code": "us-east1", "region_name": "US East (South Carolina)", "cloud_provider": "GCP", "country": "United States", "city": "South Carolina", "description": "GCP US East - South Carolina"},
    {"region_code": "us-west1", "region_name": "US West (Oregon)", "cloud_provider": "GCP", "country": "United States", "city": "Oregon", "description": "GCP US West - Oregon"},
    {"region_code": "us-west2", "region_name": "US West (Los Angeles)", "cloud_provider": "GCP", "country": "United States", "city": "Los Angeles", "description": "GCP US West - Los Angeles"},
    {"region_code": "europe-west1", "region_name": "Europe West (Belgium)", "cloud_provider": "GCP", "country": "Belgium", "city": "Brussels", "description": "GCP Europe West - Belgium"},
    {"region_code": "europe-west2", "region_name": "Europe West (London)", "cloud_provider": "GCP", "country": "United Kingdom", "city": "London", "description": "GCP Europe West - London"},
    {"region_code": "europe-west3", "region_name": "Europe West (Frankfurt)", "cloud_provider": "GCP", "country": "Germany", "city": "Frankfurt", "description": "GCP Europe West - Frankfurt"},
    {"region_code": "europe-west4", "region_name": "Europe West (Netherlands)", "cloud_provider": "GCP", "country": "Netherlands", "city": "Amsterdam", "description": "GCP Europe West - Netherlands"},
    {"region_code": "asia-southeast1", "region_name": "Asia Southeast (Singapore)", "cloud_provider": "GCP", "country": "Singapore", "city": "Singapore", "description": "GCP Asia Southeast - Singapore"},
    {"region_code": "asia-northeast1", "region_name": "Asia Northeast (Tokyo)", "cloud_provider": "GCP", "country": "Japan", "city": "Tokyo", "description": "GCP Asia Northeast - Tokyo"},
    {"region_code": "asia-northeast2", "region_name": "Asia Northeast (Seoul)", "cloud_provider": "GCP", "country": "South Korea", "city": "Seoul", "description": "GCP Asia Northeast - Seoul"},
    {"region_code": "asia-south1", "region_name": "Asia South (Mumbai)", "cloud_provider": "GCP", "country": "India", "city": "Mumbai", "description": "GCP Asia South - Mumbai"},
    {"region_code": "australia-southeast1", "region_name": "Australia Southeast (Sydney)", "cloud_provider": "GCP", "country": "Australia", "city": "Sydney", "description": "GCP Australia Southeast - Sydney"},

    # Azure Regions
    {"region_code": "eastus", "region_name": "East US", "cloud_provider": "Azure", "country": "United States", "city": "Virginia", "description": "Azure East US - Virginia"},
    {"region_code": "westus", "region_name": "West US", "cloud_provider": "Azure", "country": "United States", "city": "California", "description": "Azure West US - California"},
    {"region_code": "centralus", "region_name": "Central US", "cloud_provider": "Azure", "country": "United States", "city": "Iowa", "description": "Azure Central US - Iowa"},
    {"region_code": "westeurope", "region_name": "West Europe", "cloud_provider": "Azure", "country": "Netherlands", "city": "Amsterdam", "description": "Azure West Europe - Netherlands"},
    {"region_code": "northeurope", "region_name": "North Europe", "cloud_provider": "Azure", "country": "Ireland", "city": "Dublin", "description": "Azure North Europe - Ireland"},
    {"region_code": "southeastasia", "region_name": "Southeast Asia", "cloud_provider": "Azure", "country": "Singapore", "city": "Singapore", "description": "Azure Southeast Asia - Singapore"},
    {"region_code": "eastasia", "region_name": "East Asia", "cloud_provider": "Azure", "country": "Hong Kong", "city": "Hong Kong", "description": "Azure East Asia - Hong Kong"},
    {"region_code": "australiaeast", "region_name": "Australia East", "cloud_provider": "Azure", "country": "Australia", "city": "Sydney", "description": "Azure Australia East - Sydney"},
    {"region_code": "brazilsouth", "region_name": "Brazil South", "cloud_provider": "Azure", "country": "Brazil", "city": "São Paulo", "description": "Azure Brazil South - São Paulo"},

    # Aiven Regions
    {"region_code": "aws-eu-west-1", "region_name": "AWS EU West (Ireland)", "cloud_provider": "Aiven", "country": "Ireland", "city": "Dublin", "description": "Aiven AWS EU West - Ireland"},
    {"region_code": "aws-us-east-1", "region_name": "AWS US East (Virginia)", "cloud_provider": "Aiven", "country": "United States", "city": "Virginia", "description": "Aiven AWS US East - Virginia"},
    {"region_code": "aws-us-west-2", "region_name": "AWS US West (Oregon)", "cloud_provider": "Aiven", "country": "United States", "city": "Oregon", "description": "Aiven AWS US West - Oregon"},
    {"region_code": "gcp-europe-west1", "region_name": "GCP Europe West (Belgium)", "cloud_provider": "Aiven", "country": "Belgium", "city": "Brussels", "description": "Aiven GCP Europe West - Belgium"},
    {"region_code": "gcp-us-central1", "region_name": "GCP US Central (Iowa)", "cloud_provider": "Aiven", "country": "United States", "city": "Iowa", "description": "Aiven GCP US Central - Iowa"},
    {"region_code": "do-nyc1", "region_name": "DigitalOcean NYC1", "cloud_provider": "Aiven", "country": "United States", "city": "New York", "description": "Aiven DigitalOcean NYC1"},
    {"region_code": "do-ams1", "region_name": "DigitalOcean AMS1", "cloud_provider": "Aiven", "country": "Netherlands", "city": "Amsterdam", "description": "Aiven DigitalOcean AMS1"},
]

async def populate_locations():
    """Populate locations table with region data."""
    dsn = get_dsn()
    if not dsn:
        print("❌ No database connection string configured")
        return
    
    print("🌍 Populating locations table with region data...")
    
    try:
        async with get_connection(dsn) as conn:
            # Clear existing data
            await conn.execute("DELETE FROM locations")
            print("📝 Cleared existing location data")
            
            # Insert new data
            for location_data in LOCATION_DATA:
                region_code = location_data["region_code"]
                coordinates = REGION_COORDINATES.get(region_code)
                
                if coordinates:
                    await conn.execute("""
                        INSERT INTO locations (
                            region_code, region_name, cloud_provider, latitude, longitude,
                            country, city, description, is_active
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """, 
                    location_data["region_code"],
                    location_data["region_name"],
                    location_data["cloud_provider"],
                    Decimal(str(coordinates["lat"])),
                    Decimal(str(coordinates["lng"])),
                    location_data["country"],
                    location_data["city"],
                    location_data["description"],
                    True)
                    
                    print(f"✅ Added: {location_data['region_code']} ({location_data['cloud_provider']})")
                else:
                    print(f"⚠️  Missing coordinates for: {region_code}")
            
            print(f"\n🎉 Successfully populated {len(LOCATION_DATA)} locations!")
            
            # Verify data
            count = await conn.fetchval("SELECT COUNT(*) FROM locations")
            print(f"📊 Total locations in database: {count}")
        
    except Exception as e:
        print(f"❌ Error populating locations: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(populate_locations())