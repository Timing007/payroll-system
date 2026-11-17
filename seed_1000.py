"""Seed 1,000 realistic employees across 6 departments for Payroll Management System."""
import random
import csv
from pathlib import Path

FIRST_NAMES = [
    "Aarav", "Aditi", "Alex", "Alice", "Amara", "Amit", "Ananya", "Andrew", "Anika", "Anthony",
    "Arjun", "Ashley", "Ayush", "Benjamin", "Bhavya", "Brandon", "Brian", "Carlos", "Carol", "Catherine",
    "Chloe", "Chris", "Daniel", "David", "Deepak", "Dev", "Divya", "Edward", "Elena", "Emily",
    "Emma", "Ethan", "Eve", "Frank", "Gaurav", "Grace", "Hannah", "Harsh", "Ian", "Isha",
    "Jack", "Jacob", "James", "Jasmine", "Jason", "Jessica", "John", "Jonathan", "Jordan", "Joseph",
    "Joshua", "Kabir", "Karan", "Kavya", "Kevin", "Khushi", "Kunal", "Laura", "Leo", "Liam",
    "Lucas", "Madhav", "Manish", "Marcus", "Maria", "Mark", "Maya", "Meera", "Michael", "Mira",
    "Mohit", "Naveen", "Neha", "Nicholas", "Nikhil", "Nisha", "Noah", "Oliver", "Olivia", "Patrick",
    "Pooja", "Pranav", "Priya", "Rahul", "Raj", "Rani", "Ravi", "Rhea", "Rishi", "Rohan",
    "Rohit", "Ryan", "Sachin", "Sam", "Sameer", "Samuel", "Sanjay", "Sara", "Sarah", "Shreya",
    "Siddharth", "Sneha", "Sophia", "Sourav", "Sunil", "Suresh", "Tanvi", "Tara", "Thomas", "Trisha",
    "Tyler", "Utkarsh", "Varun", "Vikas", "Vikram", "Vinay", "William", "Yash", "Zara", "Zoe"
]

LAST_NAMES = [
    "Agarwal", "Anderson", "Banerjee", "Bhatia", "Brown", "Chakraborty", "Chawla", "Chen", "Clark", "Das",
    "Davis", "Deshmukh", "Dhawan", "Dubey", "Evans", "Garcia", "Ghosh", "Gupta", "Hall", "Harris",
    "Iyer", "Jackson", "Jain", "Johnson", "Joshi", "Kapoor", "Khan", "Khanna", "Kim", "Kulkarni",
    "Kumar", "Lee", "Lewis", "Malhotra", "Martin", "Mehta", "Miller", "Mishra", "Mitra", "Mukherjee",
    "Nair", "Narang", "Nelson", "Pandey", "Patel", "Pillai", "Prasad", "Raman", "Rao", "Reddy",
    "Robinson", "Rodriguez", "Roy", "Sahni", "Saxena", "Sen", "Sengupta", "Seth", "Sharma", "Shukla",
    "Singh", "Sinha", "Smith", "Soni", "Srivastava", "Taylor", "Tiwari", "Tripathi", "Varma", "Verma",
    "Walker", "Wang", "White", "Williams", "Wilson", "Wright", "Yadav", "Young", "Zhang", "Zimmerman"
]

DEPARTMENTS = [
    ("Engineering", 0.28),      # 28% (~280)
    ("Sales", 0.22),            # 22% (~220)
    ("Marketing", 0.15),        # 15% (~150)
    ("Product", 0.13),          # 13% (~130)
    ("Finance", 0.12),          # 12% (~120)
    ("Human Resources", 0.10)   # 10% (~100)
]

EMP_TYPES = [
    ("full_time", 0.60),  # 60%
    ("part_time", 0.25),  # 25%
    ("contract", 0.15)    # 15%
]

def generate_employees(count: int = 1000):
    random.seed(42)
    dept_names, dept_weights = zip(*DEPARTMENTS)
    type_names, type_weights = zip(*EMP_TYPES)

    employees = []
    used_names = set()

    for i in range(1, count + 1):
        emp_id = f"EMP{i:04d}"
        
        # Unique realistic full name
        while True:
            fn = random.choice(FIRST_NAMES)
            ln = random.choice(LAST_NAMES)
            name = f"{fn} {ln}"
            if name not in used_names or len(used_names) >= len(FIRST_NAMES) * len(LAST_NAMES):
                used_names.add(name)
                break

        dept = random.choices(dept_names, weights=dept_weights)[0]
        emp_type = random.choices(type_names, weights=type_weights)[0]

        if emp_type == "full_time":
            # Realistic salary distribution across seniorities (₹40,000 to ₹220,000)
            base_tier = random.choices(
                [
                    random.randint(40000, 65000),    # Junior / Associate
                    random.randint(65001, 110000),   # Mid-Level / Senior
                    random.randint(110001, 160000),  # Lead / Staff
                    random.randint(160001, 220000),  # Principal / Director
                ],
                weights=[0.35, 0.40, 0.18, 0.07]
            )[0]
            hra_pct = random.choice([15.0, 18.0, 20.0, 22.0, 25.0])
            da_pct = random.choice([5.0, 8.0, 10.0, 12.0])
            tax_pct = random.choice([5.0, 10.0, 15.0, 20.0])
            pf_pct = 12.0  # Statutory 12% PF

            employees.append({
                "emp_id": emp_id,
                "name": name,
                "department": dept,
                "emp_type": emp_type,
                "base_pay": str(base_tier),
                "extra1": str(hra_pct),
                "extra2": str(da_pct),
                "extra3": str(tax_pct),
                "extra4": str(pf_pct)
            })

        elif emp_type == "part_time":
            hourly_rate = random.choice([200, 250, 300, 350, 400, 450, 500, 550, 600])
            # Hours worked: 20 to 55 (overtime > 40)
            hours_worked = random.choice([20, 25, 30, 35, 38, 40, 42, 45, 48, 50, 52, 55])
            employees.append({
                "emp_id": emp_id,
                "name": name,
                "department": dept,
                "emp_type": emp_type,
                "base_pay": "0",
                "extra1": str(hourly_rate),
                "extra2": str(hours_worked),
                "extra3": "0",
                "extra4": "0"
            })

        else:  # contract
            project_fee = random.choice([
                50000, 65000, 75000, 85000, 95000, 110000, 125000, 140000, 160000, 180000, 200000, 250000, 300000
            ])
            employees.append({
                "emp_id": emp_id,
                "name": name,
                "department": dept,
                "emp_type": emp_type,
                "base_pay": "0",
                "extra1": str(project_fee),
                "extra2": "0",
                "extra3": "0",
                "extra4": "0"
            })

    return employees

if __name__ == "__main__":
    out_path = Path(__file__).parent / "data" / "employees.csv"
    emps = generate_employees(1000)

    fieldnames = ["emp_id", "name", "department", "emp_type", "base_pay", "extra1", "extra2", "extra3", "extra4"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(emps)

    print(f"Successfully generated {len(emps)} employees into {out_path}")
