// localStorage management for FeminineCare Tracker
class FeminineCareStorage {
    constructor() {
        this.userKey = 'feminineCareUser';
        this.periodsKey = 'feminineCarePeriods';
        this.productsKey = 'feminineCareProducts';
        this.medicationsKey = 'feminineCareMedications';
        this.settingsKey = 'feminineCareSettings';
        this.historyKey = 'feminineCareHistory';
    }

    // User management
    getCurrentUser() {
        return this.getData(this.userKey);
    }

    setCurrentUser(user) {
        this.setData(this.userKey, user);
    }

    // Period management
    getPeriods() {
        return this.getData(this.periodsKey) || [];
    }

    savePeriod(period) {
        const periods = this.getPeriods();
        if (period.id) {
            // Update existing period
            const index = periods.findIndex(p => p.id === period.id);
            if (index !== -1) {
                periods[index] = period;
            }
        } else {
            // Add new period
            period.id = this.generateId();
            period.created_at = new Date().toISOString();
            periods.unshift(period);
        }
        this.setData(this.periodsKey, periods);
        return period;
    }

    deletePeriod(periodId) {
        const periods = this.getPeriods().filter(p => p.id !== periodId);
        this.setData(this.periodsKey, periods);
    }

    // Product management
    getProducts() {
        return this.getData(this.productsKey) || [];
    }

    saveProduct(product) {
        const products = this.getProducts();
        if (product.id) {
            // Update existing product
            const index = products.findIndex(p => p.id === product.id);
            if (index !== -1) {
                products[index] = product;
            }
        } else {
            // Add new product
            product.id = this.generateId();
            product.created_at = new Date().toISOString();
            product.initial_quantity = parseInt(product.quantity);
            products.push(product);
        }
        this.setData(this.productsKey, products);
        return product;
    }

    deleteProduct(productId) {
        const products = this.getProducts().filter(p => p.id !== productId);
        this.setData(this.productsKey, products);
    }

    useProduct(productId) {
        const products = this.getProducts();
        const product = products.find(p => p.id === productId);
        if (product && product.quantity > 0) {
            product.quantity--;
            this.setData(this.productsKey, products);
            
            // Add to history
            this.addToHistory('product', {
                product_id: productId,
                product_name: product.name,
                action: 'used'
            });
            
            return true;
        }
        return false;
    }

    // Medication management
    getMedications() {
        return this.getData(this.medicationsKey) || [];
    }

    saveMedication(medication) {
        const medications = this.getMedications();
        if (medication.id) {
            // Update existing medication
            const index = medications.findIndex(m => m.id === medication.id);
            if (index !== -1) {
                medications[index] = medication;
            }
        } else {
            // Add new medication
            medication.id = this.generateId();
            medication.created_at = new Date().toISOString();
            medication.initial_quantity = parseInt(medication.quantity);
            medication.next_dose = this.calculateNextDose(medication);
            medications.push(medication);
        }
        this.setData(this.medicationsKey, medications);
        return medication;
    }

    deleteMedication(medicationId) {
        const medications = this.getMedications().filter(m => m.id !== medicationId);
        this.setData(this.medicationsKey, medications);
    }

    takeMedication(medicationId) {
        const medications = this.getMedications();
        const medication = medications.find(m => m.id === medicationId);
        if (medication && medication.quantity > 0) {
            medication.quantity--;
            medication.next_dose = this.calculateNextDose(medication);
            this.setData(this.medicationsKey, medications);
            
            // Add to history
            this.addToHistory('medication', {
                medication_id: medicationId,
                medication_name: medication.name,
                dosage: medication.dosage,
                action: 'taken'
            });
            
            return true;
        }
        return false;
    }

    // Settings management
    getSettings() {
        const defaultSettings = {
            cycle_reminders: true,
            medication_reminders: true,
            supply_alerts: false,
            notification_sounds: true,
            passcode_lock: false
        };
        return this.getData(this.settingsKey) || defaultSettings;
    }

    saveSettings(settings) {
        this.setData(this.settingsKey, settings);
    }

    // History management
    getHistory(type = null) {
        const allHistory = this.getData(this.historyKey) || [];
        if (type) {
            return allHistory.filter(item => item.type === type);
        }
        return allHistory;
    }

    addToHistory(type, data) {
        const history = this.getHistory();
        history.unshift({
            type: type,
            data: data,
            timestamp: new Date().toISOString()
        });
        this.setData(this.historyKey, history);
    }

    // Helper methods
    calculateNextDose(medication) {
        const now = new Date();
        let nextDose = new Date();
        
        switch (medication.frequency) {
            case 'daily':
                if (medication.time_of_day === 'morning') {
                    nextDose.setHours(8, 0, 0, 0);
                } else {
                    nextDose.setHours(20, 0, 0, 0);
                }
                if (nextDose < now) {
                    nextDose.setDate(nextDose.getDate() + 1);
                }
                break;
            case 'weekly':
                nextDose.setDate(now.getDate() + 7);
                break;
            case 'monthly':
                nextDose.setMonth(now.getMonth() + 1);
                break;
            default: // as-needed
                nextDose = now;
        }
        
        return nextDose.toISOString();
    }

    calculateCycleStats() {
        const periods = this.getPeriods();
        
        if (periods.length === 0) {
            return {
                average_length: 28,
                last_period: null,
                next_period: null,
                fertility_window: null,
                current_day: 1,
                days_until_next_period: null,
                days_until_ovulation: null
            };
        }
        
        const lastPeriod = new Date(periods[0].start_date);
        const today = new Date();
        const currentDay = Math.floor((today - lastPeriod) / (1000 * 60 * 60 * 24)) + 1;
        
        let avgLength = 28;
        if (periods.length >= 2) {
            const cycleLengths = [];
            for (let i = 0; i < periods.length - 1; i++) {
                const startCurrent = new Date(periods[i].start_date);
                const startPrevious = new Date(periods[i + 1].start_date);
                const cycleLength = Math.floor((startCurrent - startPrevious) / (1000 * 60 * 60 * 24));
                cycleLengths.push(cycleLength);
            }
            avgLength = Math.round(cycleLengths.reduce((a, b) => a + b, 0) / cycleLengths.length);
        }
        
        const nextPeriod = new Date(lastPeriod);
        nextPeriod.setDate(lastPeriod.getDate() + avgLength);
        
        const ovulationDay = new Date(nextPeriod);
        ovulationDay.setDate(nextPeriod.getDate() - 14);
        
        const fertilityStart = new Date(ovulationDay);
        fertilityStart.setDate(ovulationDay.getDate() - 5);
        
        const fertilityEnd = new Date(ovulationDay);
        fertilityEnd.setDate(ovulationDay.getDate() + 1);
        
        const daysUntilNextPeriod = Math.floor((nextPeriod - today) / (1000 * 60 * 60 * 24));
        const daysUntilOvulation = Math.floor((ovulationDay - today) / (1000 * 60 * 60 * 24));
        
        return {
            average_length: avgLength,
            last_period: this.formatDate(lastPeriod),
            next_period: this.formatDate(nextPeriod),
            fertility_window: `${this.formatDate(fertilityStart)} - ${this.formatDate(fertilityEnd)}`,
            current_day: currentDay,
            days_until_next_period: Math.max(0, daysUntilNextPeriod),
            days_until_ovulation: Math.max(0, daysUntilOvulation)
        };
    }

    formatDate(date) {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }

    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    getData(key) {
        try {
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : null;
        } catch (error) {
            console.error('Error reading from localStorage:', error);
            return null;
        }
    }

    setData(key, data) {
        try {
            localStorage.setItem(key, JSON.stringify(data));
            return true;
        } catch (error) {
            console.error('Error writing to localStorage:', error);
            return false;
        }
    }

    // Initialize with sample data if empty
    initializeSampleData() {
        if (this.getProducts().length === 0) {
            const sampleProducts = [
                {
                    id: 'sample1',
                    name: 'Regular Tampons',
                    category: 'tampons',
                    quantity: 12,
                    initial_quantity: 20,
                    created_at: new Date().toISOString()
                },
                {
                    id: 'sample2',
                    name: 'Overnight Pads',
                    category: 'pads',
                    quantity: 8,
                    initial_quantity: 15,
                    created_at: new Date().toISOString()
                }
            ];
            this.setData(this.productsKey, sampleProducts);
        }

        if (this.getMedications().length === 0) {
            const sampleMeds = [
                {
                    id: 'sample1',
                    name: 'Iron Supplement',
                    dosage: '1 Tablet',
                    frequency: 'daily',
                    time_of_day: 'morning',
                    quantity: 30,
                    initial_quantity: 30,
                    next_dose: this.calculateNextDose({
                        frequency: 'daily',
                        time_of_day: 'morning'
                    }),
                    created_at: new Date().toISOString()
                }
            ];
            this.setData(this.medicationsKey, sampleMeds);
        }
    }
}

// Create global instance
const feminineCareStorage = new FeminineCareStorage();