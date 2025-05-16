import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import argparse
import sys

# Try to import matplotlib but don't fail if it's not available
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: Matplotlib not installed. Visualization features will be disabled.")

class DerivTradeDashboard:
    def __init__(self, log_file="trade_log.csv"):
        self.log_file = log_file
        self.trades_df = None
        
    def load_data(self):
        """Load and process trade log data"""
        if not os.path.exists(self.log_file):
            print(f"Error: Trade log file '{self.log_file}' not found.")
            return False
            
        try:
            # Load trade log
            self.trades_df = pd.read_csv(self.log_file)
            
            # Convert time strings to datetime objects
            self.trades_df['time'] = pd.to_datetime(self.trades_df['time'])
            
            # Ensure profit column is numeric
            if 'profit' in self.trades_df.columns:
                self.trades_df['profit'] = pd.to_numeric(self.trades_df['profit'], errors='coerce')
            else:
                self.trades_df['profit'] = 0.0
                
            # Filter out pending trades for analysis
            self.completed_trades = self.trades_df[self.trades_df['result'].isin(['WIN', 'LOSS'])]
            
            return True
        except Exception as e:
            print(f"Error loading trade data: {e}")
            return False
    
    def show_summary(self):
        """Display overall trading summary"""
        if self.trades_df is None:
            print("No data loaded. Run load_data() first.")
            return
            
        print("\n" + "="*60)
        print("TRADING PERFORMANCE SUMMARY")
        print("="*60)
        
        # Basic stats
        total_trades = len(self.completed_trades)
        if total_trades == 0:
            print("No completed trades found in log.")
            return
            
        wins = len(self.completed_trades[self.completed_trades['result'] == 'WIN'])
        losses = len(self.completed_trades[self.completed_trades['result'] == 'LOSS'])
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        
        # Calculate profit metrics if available
        if 'profit' in self.completed_trades.columns and not self.completed_trades['profit'].isna().all():
            total_profit = self.completed_trades['profit'].sum()
            avg_win = self.completed_trades[self.completed_trades['result'] == 'WIN']['profit'].mean()
            avg_loss = self.completed_trades[self.completed_trades['result'] == 'LOSS']['profit'].mean()
            max_win = self.completed_trades['profit'].max()
            max_loss = self.completed_trades['profit'].min()
            profit_factor = abs(self.completed_trades[self.completed_trades['profit'] > 0]['profit'].sum() / 
                              self.completed_trades[self.completed_trades['profit'] < 0]['profit'].sum()) if self.completed_trades[self.completed_trades['profit'] < 0]['profit'].sum() != 0 else float('inf')
            
            # Display profit metrics
            print(f"Total P/L: ${total_profit:.2f}")
            print(f"Average Win: ${avg_win:.2f} | Average Loss: ${avg_loss:.2f}")
            print(f"Largest Win: ${max_win:.2f} | Largest Loss: ${max_loss:.2f}")
            print(f"Profit Factor: {profit_factor:.2f}")
        
        # Display trade metrics
        print(f"Total Trades: {total_trades} (Wins: {wins}, Losses: {losses})")
        print(f"Win Rate: {win_rate:.1f}%")
        
        # Direction analysis
        calls = len(self.completed_trades[self.completed_trades['direction'] == 'CALL'])
        puts = len(self.completed_trades[self.completed_trades['direction'] == 'PUT'])
        call_wins = len(self.completed_trades[(self.completed_trades['direction'] == 'CALL') & 
                                            (self.completed_trades['result'] == 'WIN')])
        put_wins = len(self.completed_trades[(self.completed_trades['direction'] == 'PUT') & 
                                           (self.completed_trades['result'] == 'WIN')])
        
        call_win_rate = (call_wins / calls) * 100 if calls > 0 else 0
        put_win_rate = (put_wins / puts) * 100 if puts > 0 else 0
        
        print(f"CALL Trades: {calls} (Win Rate: {call_win_rate:.1f}%)")
        print(f"PUT Trades: {puts} (Win Rate: {put_win_rate:.1f}%)")
        
        # Date range
        if len(self.completed_trades) > 0:
            first_trade = self.completed_trades['time'].min()
            last_trade = self.completed_trades['time'].max()
            date_range = (last_trade - first_trade).days + 1
            
            print(f"\nDate Range: {first_trade.strftime('%Y-%m-%d')} to {last_trade.strftime('%Y-%m-%d')} ({date_range} days)")
            print(f"Average Trades Per Day: {total_trades / date_range:.1f}")
        
        print("="*60)
    
    def plot_equity_curve(self):
        """Plot equity curve over time"""
        if not MATPLOTLIB_AVAILABLE:
            print("Cannot generate equity curve: matplotlib is not installed.")
            return
            
        if self.trades_df is None or len(self.completed_trades) == 0:
            print("No completed trade data available.")
            return
            
        if 'profit' not in self.completed_trades.columns or self.completed_trades['profit'].isna().all():
            print("Profit data not available in trade log.")
            return
        
        # Sort by time
        sorted_trades = self.completed_trades.sort_values('time')
        
        # Calculate cumulative profit
        sorted_trades['cumulative_profit'] = sorted_trades['profit'].cumsum()
        
        # Create plot
        plt.figure(figsize=(12, 6))
        plt.plot(sorted_trades['time'], sorted_trades['cumulative_profit'], 'b-', linewidth=2)
        plt.axhline(y=0, color='r', linestyle='-', alpha=0.3)
        plt.fill_between(sorted_trades['time'], sorted_trades['cumulative_profit'], 
                        where=(sorted_trades['cumulative_profit'] >= 0), 
                        color='green', alpha=0.3)
        plt.fill_between(sorted_trades['time'], sorted_trades['cumulative_profit'], 
                        where=(sorted_trades['cumulative_profit'] < 0), 
                        color='red', alpha=0.3)
        
        # Formatting
        plt.title('Equity Curve', fontsize=14)
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Profit ($)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Add annotations
        final_profit = sorted_trades['cumulative_profit'].iloc[-1]
        color = 'green' if final_profit >= 0 else 'red'
        plt.annotate(f'${final_profit:.2f}', 
                    xy=(sorted_trades['time'].iloc[-1], final_profit),
                    xytext=(8, 0), textcoords='offset points',
                    fontsize=12, fontweight='bold', color=color)
        
        plt.show()
    
    def plot_win_loss_distribution(self):
        """Plot win/loss distribution by time of day"""
        if not MATPLOTLIB_AVAILABLE:
            print("Cannot generate win/loss distribution: matplotlib is not installed.")
            return
            
        if self.trades_df is None or len(self.completed_trades) == 0:
            print("No completed trade data available.")
            return
        
        # Extract hour from trade times
        self.completed_trades['hour'] = self.completed_trades['time'].dt.hour
        
        # Group by hour and result
        hourly_results = pd.crosstab(self.completed_trades['hour'], self.completed_trades['result'])
        
        if 'WIN' not in hourly_results.columns:
            hourly_results['WIN'] = 0
        if 'LOSS' not in hourly_results.columns:
            hourly_results['LOSS'] = 0
            
        # Fill missing hours with 0
        all_hours = pd.DataFrame(index=range(24))
        hourly_results = hourly_results.reindex(all_hours.index, fill_value=0)
        
        # Plot
        plt.figure(figsize=(12, 6))
        
        # Create bar chart
        width = 0.35
        x = np.arange(24)
        
        plt.bar(x - width/2, hourly_results['WIN'], width, label='Wins', color='green', alpha=0.7)
        plt.bar(x + width/2, hourly_results['LOSS'], width, label='Losses', color='red', alpha=0.7)
        
        # Formatting
        plt.title('Win/Loss Distribution by Hour (UTC)', fontsize=14)
        plt.xlabel('Hour', fontsize=12)
        plt.ylabel('Number of Trades', fontsize=12)
        plt.xticks(range(24))
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        
        plt.show()
    
    def plot_weekly_performance(self):
        """Plot performance by day of week"""
        if not MATPLOTLIB_AVAILABLE:
            print("Cannot generate weekly performance: matplotlib is not installed.")
            return
            
        if self.trades_df is None or len(self.completed_trades) == 0:
            print("No completed trade data available.")
            return
            
        if 'profit' not in self.completed_trades.columns or self.completed_trades['profit'].isna().all():
            print("Profit data not available in trade log.")
            return
        
        # Extract day of week
        self.completed_trades['day_of_week'] = self.completed_trades['time'].dt.day_name()
        
        # Calculate metrics by day
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        days_profit = self.completed_trades.groupby('day_of_week')['profit'].sum().reindex(day_order)
        days_counts = self.completed_trades.groupby(['day_of_week', 'result']).size().unstack().reindex(day_order)
        
        if 'WIN' not in days_counts.columns:
            days_counts['WIN'] = 0
        if 'LOSS' not in days_counts.columns:
            days_counts['LOSS'] = 0
            
        days_counts = days_counts.fillna(0)
        
        # Calculate win rate
        days_counts['Total'] = days_counts['WIN'] + days_counts['LOSS']
        days_counts['Win_Rate'] = (days_counts['WIN'] / days_counts['Total']) * 100
        days_counts['Win_Rate'] = days_counts['Win_Rate'].fillna(0)
        
        # Create plot with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10), gridspec_kw={'height_ratios': [1.5, 1]})
        
        # Profit by day plot
        colors = ['green' if x >= 0 else 'red' for x in days_profit]
        ax1.bar(days_profit.index, days_profit, color=colors, alpha=0.7)
        ax1.set_title('Profit by Day of Week', fontsize=14)
        ax1.set_ylabel('Profit ($)', fontsize=12)
        ax1.grid(True, axis='y', alpha=0.3)
        
        # Add profit values on bars
        for i, v in enumerate(days_profit):
            if pd.notnull(v):
                ax1.text(i, v + (5 if v >= 0 else -5), 
                        f'${v:.2f}', 
                        ha='center', 
                        fontweight='bold',
                        color='black')
        
        # Win rate by day plot
        ax2.plot(days_counts.index, days_counts['Win_Rate'], 'o-', color='blue', linewidth=2, markersize=8)
        ax2.set_title('Win Rate by Day of Week', fontsize=14)
        ax2.set_ylabel('Win Rate (%)', fontsize=12)
        ax2.set_ylim(0, 100)  # Win rate is percentage
        ax2.grid(True, alpha=0.3)
        
        # Add win rate values
        for i, v in enumerate(days_counts['Win_Rate']):
            if pd.notnull(v):
                ax2.text(i, v + 2, f'{v:.1f}%', ha='center', fontweight='bold')
        
        # Add trade counts
        for i, (wins, losses) in enumerate(zip(days_counts['WIN'], days_counts['LOSS'])):
            if pd.notnull(wins) and pd.notnull(losses):
                ax2.text(i, 10, f'W: {int(wins)} L: {int(losses)}', ha='center')
        
        plt.tight_layout()
        plt.show()
    
    def run_dashboard(self):
        """Run the full dashboard analysis"""
        if not self.load_data():
            return
            
        self.show_summary()
        
        if MATPLOTLIB_AVAILABLE:
            print("\nGenerating visualizations...")
            self.plot_equity_curve()
            self.plot_win_loss_distribution()
            self.plot_weekly_performance()
        else:
            print("\nVisualizations are disabled due to missing matplotlib. Install matplotlib to enable visualizations.")
            
            # Provide a text-based summary of data that would be in visualizations
            if len(self.completed_trades) > 0 and 'profit' in self.completed_trades.columns:
                print("\nTEXT SUMMARY OF TRADING DATA:")
                
                # Equity curve summary
                sorted_trades = self.completed_trades.sort_values('time')
                sorted_trades['cumulative_profit'] = sorted_trades['profit'].cumsum()
                final_profit = sorted_trades['cumulative_profit'].iloc[-1]
                print(f"Final cumulative P/L: ${final_profit:.2f}")
                
                # Hourly distribution summary
                self.completed_trades['hour'] = self.completed_trades['time'].dt.hour
                hourly_win_counts = self.completed_trades[self.completed_trades['result'] == 'WIN'].groupby('hour').size()
                hourly_loss_counts = self.completed_trades[self.completed_trades['result'] == 'LOSS'].groupby('hour').size()
                
                best_hour = hourly_win_counts.idxmax() if not hourly_win_counts.empty else None
                worst_hour = hourly_loss_counts.idxmax() if not hourly_loss_counts.empty else None
                
                if best_hour is not None:
                    print(f"Best trading hour: {best_hour}:00 UTC ({hourly_win_counts[best_hour]} wins)")
                if worst_hour is not None:
                    print(f"Worst trading hour: {worst_hour}:00 UTC ({hourly_loss_counts[worst_hour]} losses)")
                
                # Weekly performance summary
                self.completed_trades['day_of_week'] = self.completed_trades['time'].dt.day_name()
                day_profit = self.completed_trades.groupby('day_of_week')['profit'].sum()
                best_day = day_profit.idxmax() if not day_profit.empty else None
                worst_day = day_profit.idxmin() if not day_profit.empty else None
                
                if best_day is not None:
                    print(f"Most profitable day: {best_day} (${day_profit[best_day]:.2f})")
                if worst_day is not None:
                    print(f"Least profitable day: {worst_day} (${day_profit[worst_day]:.2f})")
        
def main():
    parser = argparse.ArgumentParser(description='Deriv Trade Performance Dashboard')
    parser.add_argument('--log', type=str, default='trade_log.csv', help='Path to trade log CSV file')
    
    # Handle unrecognized arguments by allowing them
    args, unknown = parser.parse_known_args()
    
    if unknown:
        print(f"Warning: Ignoring unrecognized arguments: {' '.join(unknown)}")
    
    dashboard = DerivTradeDashboard(args.log)
    dashboard.run_dashboard()

if __name__ == "__main__":
    main()