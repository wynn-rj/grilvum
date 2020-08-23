"""A extension that adds party funds utilities"""
import sqlite3
from discord.ext import commands
from utils.config_reader import YAMLConfigReader
from utils.logger import Logger

class BagOfHolding(commands.Cog):
    """Extension class"""
    def __init__(self, bot):
        self.bot = bot
        self.config = YAMLConfigReader()

    def get_party_bag(self, guild, name):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT Item, Quantity FROM bag_of_holding_items WHERE Bag_ID IN (SELECT ID FROM bag_of_holding WHERE Name = ? and Guild_ID = ?)", (name, guild.id))
            result = cur.fetchall()
            conn.commit()
        finally:
            conn.close()
        return result 

    def add_bag(self, guild, name):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT ID FROM bag_of_holding WHERE Guild_ID = ? AND Name = ?",(guild.id, name))
            result = cur.fetchall()
            if len(result) == 0:
                cur.execute("INSERT INTO bag_of_holding VALUES (NULL, ?, ?)", (guild.id, name))
                conn.commit()
                return 1
            else:
                return 2
        except:
            return 0
        finally:
            conn.close()

    def remove_bag(self, guild, name):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()
            cur.execute("SELECT ID FROM bag_of_holding WHERE Guild_ID = ? AND Name = ?",(guild.id, name))
            result = cur.fetchall()
            if len(result) > 0:
                cur.execute("DELETE FROM bag_of_holding_items WHERE Bag_ID = (SELECT ID FROM bag_of_holding WHERE Name = ? and Guild_ID = ?)", (name, guild.id))
                cur.execute("DELETE FROM bag_of_holding WHERE Name = ? AND Guild_ID = ?", (name, guild.id)) 
                conn.commit()
                return 1
            else:
                return 2
        except:
            return 0
        finally:
            conn.close()

    def add_to_bag(self, guild, name, item, quantity):
        conn = sqlite3.connect(self.config.data.database)
        try:
            cur = conn.cursor()       
            cur.execute("SELECT Quantity FROM bag_of_holding_items WHERE Item = ? AND Bag_ID IN (SELECT ID FROM bag_of_holding WHERE Name = ? and Guild_ID = ?)", (item, name, guild.id))
            result = cur.fetchone()
            if result is not None:
                cur.execute("UPDATE bag_of_holding_items SET Quantity = ? WHERE Item = ? AND Bag_ID IN (SELECT ID FROM bag_of_holding WHERE Name = ? and Guild_ID = ?)", (int(result[0]) + int(quantity), item, name, guild.id))
            else:
                cur.execute("SELECT ID FROM bag_of_holding WHERE Name = ? AND Guild_ID = ?", (name, guild.id))
                bag_id = cur.fetchone()
                if bag_id is None:
                    return 0
                cur.execute("INSERT INTO bag_of_holding_items VALUES (NULL, ?, ?, ?)", (bag_id[0], item, quantity))
            conn.commit()
            return 1
        finally:
            conn.close()

    def remove_from_bag(self, guild, name, item, quantity):
        conn = sqlite3.connect(self.config.data.database)
        try:
            removed = 0
            cur = conn.cursor()        
            cur.execute("SELECT Quantity FROM bag_of_holding_items WHERE Item = ? AND Bag_ID = (SELECT ID FROM bag_of_holding WHERE Name = ? and Guild_ID = ?)", (item, name, guild.id))
            result = cur.fetchone()
            if result is not None:
                dif = int(result[0]) - int(quantity)
                if dif < 1:
                    cur.execute("DELETE FROM bag_of_holding_items WHERE Item = ? AND Bag_ID = (SELECT ID FROM bag_of_holding WHERE Name = ? and Guild_ID = ?)", (item, name, guild.id))
                    removed = result[0]
                else:
                    cur.execute("UPDATE bag_of_holding_items SET Quantity = ? WHERE Item = ? AND Bag_ID = (SELECT ID FROM bag_of_holding WHERE Name = ? and Guild_ID = ?)", (dif, item, name, guild.id))
                    removed = quantity
            else:
                removed = 0
            conn.commit()
            return removed
        finally:
            conn.close()

    @commands.group(pass_context=True, help="Manage bag of holding.")
    async def boh(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid subcommand')

    @boh.command()
    async def addBag(self, ctx, name):
        result = self.add_bag(ctx.guild, name)
        if result == 1:
            await ctx.send(f'{name} successfully added to your party.')
        elif result == 2:
            await ctx.send(f'{name} already exists.')
        else:
            await ctx.send(f'Error adding {name} to your party.')


    @boh.command()
    async def removeBag(self, ctx, name):
        result = self.remove_bag(ctx.guild, name)
        if result == 1:
            await ctx.send(f'{name} successfully removed to your party.')
        elif result == 2:
            await ctx.send(f'{name} not found.')
        else:
            await ctx.send(f'Error removing {name} from your party.')

    @boh.command()
    async def add(self, ctx, name, item: str, quantity = 1):
        result = self.add_to_bag(ctx.guild, name, item, quantity)
        await ctx.send(f'{result}')
        if result == 1:
            if quantity > 1:
                await ctx.send(f'{item}({quantity}) successfully added to the Bag of Holding.')
            else:
                await ctx.send(f'{item} successfully added to the Bag of Holding.')
        else:
            await ctx.send(f'Error adding {item}({quantity}) to {name}.')


    @boh.command()
    async def dump(self, ctx, name):
        party_bag = self.get_party_bag(ctx.guild, name)
        if party_bag is None:
            await ctx.send(f'Failed to get {name}.')
            return
        if len(party_bag) == 0:
            await ctx.send(f'{name} is empty.')
            return
        print_string = 'The Bag of Holding Contains:'
        for item in party_bag:
            print_string += f'\n{item[0]}'
            if item[1] > 1:
                print_string += f': {item[1]}'

        await ctx.send(print_string)


    @boh.command()
    async def remove(self, ctx, name, item: str, quantity = 1):
        result = self.remove_from_bag(ctx.guild, name, item, quantity)
        if result > 0:
            if quantity > 1:
                await ctx.send(f'{item}({result}) removed from {name}.')
            else:
                await ctx.send(f'{item} removed from {name}.')
        else:
           await ctx.send(f'{item} not found.')



def setup(bot):
    """Add the extension as a cog"""
    bot.add_cog(BagOfHolding(bot))
