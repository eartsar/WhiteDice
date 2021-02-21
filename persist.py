import aiosqlite


class DatabaseManager():
    def __init__(self, sqlite3_file):
        self.dbpath = sqlite3_file
    

    async def initialize(self):
        async with aiosqlite.connect(self.dbpath) as db:
            print("Connecting to and preparing SQLITE database...")
            await db.execute('''\
                CREATE TABLE IF NOT EXISTS PLAYER_STATS (
                    user_id int, stat varchar(255), strength int, dexterity int, constitution int,
                    intelligence int, wisdom int, charisma int, av int, ac int, hp int
                )''')
            await db.execute('CREATE TABLE IF NOT EXISTS PLAYER_MACROS (user_id int, macro varchar(255), value varchar(255))')
            print("Done.")

    
    async def get_macro(self, user, macro):
        async with aiosqlite.connect(self.dbpath) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(f"SELECT value FROM PLAYER_MACROS WHERE user_id = {user.id} AND macro = '{macro}'") as cursor:
                result = await cursor.fetchone()
                return result['value'] if result else None


    async def get_stats(self, user):
        async with aiosqlite.connect(self.dbpath) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(f'''\
                SELECT strength, dexterity, constitution, intelligence, wisdom, charisma, av, ac, hp
                FROM PLAYER_STATS
                WHERE user_id = {user.id}''') as cursor:
                result = await cursor.fetchone()
                return result if result else None


    async def upsert_stat(self, user, stat, value):
        stats = await self.get_stats(user)
        async with aiosqlite.connect(self.dbpath) as db:
            if not stats:           
                await db.execute(f'''
                    INSERT INTO PLAYER_STATS (
                        user_id, strength, dexterity, constitution, intelligence, wisdom, charisma, av, ac, hp
                    ) VALUES (
                        {user.id}, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
                    )''')
                await db.commit()

            await db.execute(f'UPDATE PLAYER_STATS SET {stat} = {value} WHERE user_id = {user.id}')
            await db.commit()


    async def upsert_macro(self, user, macro, value):
        result = await self.get_macro(user, macro)
        async with aiosqlite.connect(self.dbpath) as db:
            if not result:           
                await db.execute(f'''
                    INSERT INTO PLAYER_MACROS (
                        user_id, macro, value
                    ) VALUES (
                        {user.id}, '{macro}', NULL
                    )''')
                await db.commit()

            await db.execute(f"UPDATE PLAYER_MACROS SET value = '{value}' WHERE user_id = {user.id} AND macro = '{macro}'")
            await db.commit()

